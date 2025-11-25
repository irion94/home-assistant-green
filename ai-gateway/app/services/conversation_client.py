"""Conversation client for small talk mode with OpenAI streaming.

This module handles conversational AI responses using OpenAI GPT
with session memory and streaming output for TTS.

Supports action detection during conversation - if user says "turn on lights",
it will execute the HA action and continue the conversation.

Database Integration (Phase 2):
- Conversations are persisted to PostgreSQL for history/analytics
- In-memory cache provides fast access during active session
- Session history can be restored after container restarts
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Any
from collections import defaultdict

import httpx
import json

if TYPE_CHECKING:
    from app.models import Config
    from app.services.database import DatabaseService

from app.services.llm_tools import get_tools, get_tool_executor

logger = logging.getLogger(__name__)

# Optional: HA client and intent matcher for action detection during conversation
_ha_client = None
_intent_matcher = None

# Session storage for conversation history
_sessions: dict[str, list[dict[str, str]]] = defaultdict(list)

# Default system prompt (used if personality file not found)
_DEFAULT_SYSTEM_PROMPT = """Jesteś Jarvis - przyjazny asystent domowy.

Zasady:
1. ZAWSZE odpowiadaj po polsku (chyba że użytkownik pyta po angielsku)
2. Bądź zwięzły - krótkie odpowiedzi dla prostych pytań (1-3 zdania)
3. Bądź przyjazny i naturalny, nie robotyczny
4. Dla potwierdzeń akcji: tylko "Gotowe" lub krótka odpowiedź
5. Dla pytań: odpowiadaj konkretnie i na temat
6. Pamiętaj kontekst rozmowy

Przykłady dobrych odpowiedzi:
- "Jaka jest pogoda?" → "Nie mam dostępu do pogody, ale mogę pomóc skonfigurować czujnik."
- "Opowiedz żart" → "Dlaczego programista nosi okulary? Bo nie widzi C#!"
- "Dziękuję" → "Nie ma za co!"
- "What time is it?" → "I don't have access to the current time, but your phone does!"
"""


def _load_personality() -> str:
    """Load personality configuration from markdown file.

    Looks for personality file in this order:
    1. PERSONALITY_FILE environment variable
    2. /app/config/PERSONALITY.md (Docker default)
    3. ../config/PERSONALITY.md (local development)

    Returns:
        System prompt string from file, or default if not found
    """
    # Check environment variable first
    personality_path = os.getenv("PERSONALITY_FILE")

    if not personality_path:
        # Try default locations
        default_paths = [
            Path("/app/config/PERSONALITY.md"),
            Path(__file__).parent.parent.parent / "config" / "PERSONALITY.md",
        ]
        for path in default_paths:
            if path.exists():
                personality_path = str(path)
                break

    if personality_path and Path(personality_path).exists():
        try:
            content = Path(personality_path).read_text(encoding="utf-8")
            logger.info(f"Loaded personality from: {personality_path}")
            return content
        except Exception as e:
            logger.warning(f"Failed to load personality file: {e}")

    logger.info("Using default personality prompt")
    return _DEFAULT_SYSTEM_PROMPT


# Load personality at module initialization
CONVERSATION_SYSTEM_PROMPT = _load_personality()


class ConversationClient:
    """Client for conversational AI using OpenAI streaming.

    Supports optional database persistence for conversation history.
    When db_service is provided, all messages are saved to PostgreSQL.
    """

    def __init__(self, config: Config, db_service: DatabaseService | None = None):
        """Initialize conversation client.

        Args:
            config: Application configuration
            db_service: Optional database service for persistence
        """
        self.config = config
        self.api_key = config.openai_api_key
        self.model = config.openai_model
        self.base_url = "https://api.openai.com/v1"
        self.timeout = config.conversation_timeout
        self.db = db_service

        if not self.api_key:
            raise ValueError("OpenAI API key required for conversation mode")

        # Initialize action detection components (lazy loaded)
        self._ha_client = None
        self._intent_matcher = None

        # Track which sessions have been loaded from DB
        self._db_loaded_sessions: set[str] = set()

        db_status = "enabled" if db_service else "disabled"
        logger.info(f"ConversationClient initialized with model={self.model}, db={db_status}")

    def _get_action_handlers(self):
        """Lazy load HA client and intent matcher for action detection.

        Returns:
            Tuple of (intent_matcher, ha_client) or (None, None) if not available
        """
        if self._intent_matcher is None:
            try:
                from app.services.intent_matcher import get_intent_matcher
                from app.services.ha_client import HomeAssistantClient

                self._intent_matcher = get_intent_matcher()
                self._ha_client = HomeAssistantClient(self.config)
                logger.info("Action detection handlers initialized")
            except Exception as e:
                logger.warning(f"Could not initialize action handlers: {e}")
                return None, None

        return self._intent_matcher, self._ha_client

    def get_session(self, session_id: str) -> list[dict[str, str]]:
        """Get conversation history for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            List of message dictionaries
        """
        return _sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history for a session.

        Args:
            session_id: Unique session identifier
        """
        if session_id in _sessions:
            del _sessions[session_id]
            logger.info(f"Cleared conversation session: {session_id}")
        # Also remove from loaded tracking
        self._db_loaded_sessions.discard(session_id)

    async def _ensure_session_loaded(self, session_id: str) -> None:
        """Load session history from database if not already loaded.

        This ensures we have any previous conversation context when
        resuming a session after container restart.

        Args:
            session_id: Session identifier
        """
        # Skip if already loaded or no DB
        if session_id in self._db_loaded_sessions or not self.db:
            return

        # Skip if session already has in-memory messages
        if _sessions[session_id]:
            self._db_loaded_sessions.add(session_id)
            return

        try:
            # Load recent history from database
            history = await self.db.get_conversation_history(session_id, limit=20)
            if history:
                # Convert DB format to in-memory format
                for msg in history:
                    _sessions[session_id].append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                logger.info(f"Loaded {len(history)} messages from DB for session {session_id}")
            self._db_loaded_sessions.add(session_id)
        except Exception as e:
            logger.warning(f"Failed to load session from DB: {e}")
            self._db_loaded_sessions.add(session_id)  # Mark as loaded to avoid retries

    async def _save_message_to_db(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Save a message to the database.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
            metadata: Optional metadata (e.g., tool calls)
        """
        if not self.db:
            return

        try:
            await self.db.save_conversation(
                session_id=session_id,
                role=role,
                content=content,
                language=None,  # Could detect language later
                intent=None,
                metadata=metadata
            )
            logger.debug(f"Saved {role} message to DB: session={session_id}")
        except Exception as e:
            logger.warning(f"Failed to save message to DB: {e}")

    async def chat(self, text: str, session_id: str) -> str:
        """Send message and get response with function calling.

        Uses OpenAI function calling to let the LLM decide when to use tools
        like web search, device control, etc.

        Messages are persisted to database if db_service is configured.

        Args:
            text: User message
            session_id: Session identifier for memory

        Returns:
            AI response text
        """
        # Load session history from DB if this is a resumed session
        await self._ensure_session_loaded(session_id)

        # Get HA client for tool execution
        _, ha_client = self._get_action_handlers()
        tool_executor = get_tool_executor(ha_client)

        # Add user message to history
        _sessions[session_id].append({"role": "user", "content": text})

        # Save user message to database
        await self._save_message_to_db(session_id, "user", text)

        # Build messages with history
        messages = [
            {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
            *_sessions[session_id]
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # First call with tools
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "tools": get_tools(),
                        "tool_choice": "auto",
                        "max_tokens": 500,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()

                message = data["choices"][0]["message"]

                # Check if LLM wants to call a tool
                if message.get("tool_calls"):
                    logger.info(f"LLM requested {len(message['tool_calls'])} tool call(s)")

                    # Add assistant's tool call request to messages
                    messages.append(message)

                    # Execute each tool call
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}

                        # Execute the tool
                        result = await tool_executor.execute(tool_name, arguments)
                        logger.info(f"Tool {tool_name} result: {result[:100]}...")

                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result
                        })

                    # Get final response from LLM with tool results
                    final_response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": messages,
                            "max_tokens": 300,
                            "temperature": 0.7,
                        },
                    )
                    final_response.raise_for_status()
                    final_data = final_response.json()
                    assistant_message = final_data["choices"][0]["message"]["content"]
                else:
                    # No tool call, use direct response
                    assistant_message = message.get("content", "")

                # Add assistant response to history
                _sessions[session_id].append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # Save assistant message to database (include tool call info in metadata)
                tool_calls_metadata = None
                if message.get("tool_calls"):
                    tool_calls_metadata = {
                        "tool_calls": [
                            {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"]
                            }
                            for tc in message["tool_calls"]
                        ]
                    }
                await self._save_message_to_db(
                    session_id, "assistant", assistant_message, tool_calls_metadata
                )

                logger.info(
                    f"Conversation response: session={session_id}, "
                    f"history_length={len(_sessions[session_id])}"
                )

                return assistant_message

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Conversation error: {e}", exc_info=True)
            raise

    async def chat_stream(self, text: str, session_id: str) -> AsyncIterator[str]:
        """Send message and stream response.

        Args:
            text: User message
            session_id: Session identifier for memory

        Yields:
            Response text chunks
        """
        # Load session history from DB if this is a resumed session
        await self._ensure_session_loaded(session_id)

        # Add user message to history
        _sessions[session_id].append({"role": "user", "content": text})

        # Save user message to database
        await self._save_message_to_db(session_id, "user", text)

        # Build messages with history
        messages = [
            {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
            *_sessions[session_id]
        ]

        full_response = ""

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 150,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    yield content
                            except json.JSONDecodeError:
                                continue

            # Add full response to history
            _sessions[session_id].append({
                "role": "assistant",
                "content": full_response
            })

            # Save assistant message to database
            await self._save_message_to_db(session_id, "assistant", full_response)

            logger.info(
                f"Streamed conversation: session={session_id}, "
                f"response_length={len(full_response)}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI streaming error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Conversation streaming error: {e}", exc_info=True)
            raise

    async def chat_stream_sentences(self, text: str, session_id: str) -> AsyncIterator[str]:
        """Stream response sentence by sentence for TTS.

        Buffers streaming chunks until a complete sentence is detected,
        then yields the sentence for immediate TTS playback.

        Args:
            text: User message
            session_id: Session identifier for memory

        Yields:
            Complete sentences as they become available
        """
        # Load session history from DB if this is a resumed session
        await self._ensure_session_loaded(session_id)

        buffer = ""
        sentence_endings = {'.', '!', '?'}
        full_response = ""

        # Add user message to history
        _sessions[session_id].append({"role": "user", "content": text})

        # Save user message to database
        await self._save_message_to_db(session_id, "user", text)

        # Build messages with history
        messages = [
            {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
            *_sessions[session_id]
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 150,
                        "temperature": 0.7,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data)
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    buffer += content
                                    full_response += content

                                    # Check for complete sentences
                                    while True:
                                        # Find first sentence ending
                                        sentence_end = -1
                                        for i, char in enumerate(buffer):
                                            if char in sentence_endings:
                                                # Check if it's really end (not abbreviation)
                                                # Look for space or end of buffer after punctuation
                                                if i + 1 >= len(buffer) or buffer[i + 1] in ' \n':
                                                    sentence_end = i
                                                    break

                                        if sentence_end == -1:
                                            break

                                        # Extract and yield sentence
                                        sentence = buffer[:sentence_end + 1].strip()
                                        buffer = buffer[sentence_end + 1:].lstrip()

                                        if sentence:
                                            logger.debug(f"Yielding sentence: {sentence[:50]}...")
                                            yield sentence

                            except json.JSONDecodeError:
                                continue

            # Yield any remaining buffer
            if buffer.strip():
                logger.debug(f"Yielding remaining: {buffer.strip()[:50]}...")
                yield buffer.strip()

            # Add full response to history
            _sessions[session_id].append({
                "role": "assistant",
                "content": full_response
            })

            # Save assistant message to database
            await self._save_message_to_db(session_id, "assistant", full_response)

            logger.info(
                f"Streamed sentences: session={session_id}, "
                f"response_length={len(full_response)}"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI sentence streaming error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Sentence streaming error: {e}", exc_info=True)
            raise


# Global instance
_conversation_client: ConversationClient | None = None


def get_conversation_client(
    config: Config,
    db_service: DatabaseService | None = None
) -> ConversationClient:
    """Get or create conversation client.

    Args:
        config: Application configuration
        db_service: Optional database service for persistence

    Returns:
        ConversationClient instance
    """
    global _conversation_client
    if _conversation_client is None:
        _conversation_client = ConversationClient(config, db_service)
    return _conversation_client


def reset_conversation_client() -> None:
    """Reset the global conversation client.

    Useful for testing or when reconfiguring with different db_service.
    """
    global _conversation_client
    _conversation_client = None
