"""Conversation client for small talk mode with OpenAI streaming.

This module handles conversational AI responses using OpenAI GPT
with session memory and streaming output for TTS.

Supports action detection during conversation - if user says "turn on lights",
it will execute the HA action and continue the conversation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator
from collections import defaultdict

import httpx

if TYPE_CHECKING:
    from app.models import Config

logger = logging.getLogger(__name__)

# Optional: HA client and intent matcher for action detection during conversation
_ha_client = None
_intent_matcher = None

# Session storage for conversation history
_sessions: dict[str, list[dict[str, str]]] = defaultdict(list)

# System prompt for conversation mode
CONVERSATION_SYSTEM_PROMPT = """Jesteś Jarvis - przyjazny asystent domowy.

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


class ConversationClient:
    """Client for conversational AI using OpenAI streaming."""

    def __init__(self, config: Config):
        """Initialize conversation client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.api_key = config.openai_api_key
        self.model = config.openai_model
        self.base_url = "https://api.openai.com/v1"
        self.timeout = 30.0

        if not self.api_key:
            raise ValueError("OpenAI API key required for conversation mode")

        # Initialize action detection components (lazy loaded)
        self._ha_client = None
        self._intent_matcher = None

        logger.info(f"ConversationClient initialized with model={self.model}")

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

    async def chat(self, text: str, session_id: str) -> str:
        """Send message and get response (non-streaming).

        Checks for HA actions in the message first. If found, executes action
        and acknowledges, then optionally continues with AI response.

        Args:
            text: User message
            session_id: Session identifier for memory

        Returns:
            AI response text (or action acknowledgment + response)
        """
        # Check for HA actions in message
        intent_matcher, ha_client = self._get_action_handlers()

        if intent_matcher and ha_client:
            try:
                action = intent_matcher.match(text)
                if action and action.action not in ("none", "conversation_start", "conversation_end"):
                    logger.info(f"Detected HA action in conversation: {action.action}")
                    # Execute the action
                    result = await ha_client.call_service(action)
                    if result is not None:
                        logger.info(f"Executed HA action during conversation: {action.service}")
                        # Just acknowledge the action, don't ask AI for commentary
                        _sessions[session_id].append({"role": "user", "content": text})
                        _sessions[session_id].append({"role": "assistant", "content": "Gotowe"})
                        return "Gotowe"
                    else:
                        logger.warning(f"HA action failed: {action.service}")
                        return "Nie udało się wykonać polecenia"
            except Exception as e:
                logger.error(f"Error checking for HA action: {e}")

        # Add user message to history
        _sessions[session_id].append({"role": "user", "content": text})

        # Build messages with history
        messages = [
            {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT},
            *_sessions[session_id]
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 150,  # Keep responses short for TTS
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()

                assistant_message = data["choices"][0]["message"]["content"]

                # Add assistant response to history
                _sessions[session_id].append({
                    "role": "assistant",
                    "content": assistant_message
                })

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
        # Add user message to history
        _sessions[session_id].append({"role": "user", "content": text})

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
                                import json
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


# Global instance
_conversation_client: ConversationClient | None = None


def get_conversation_client(config: Config) -> ConversationClient:
    """Get or create conversation client.

    Args:
        config: Application configuration

    Returns:
        ConversationClient instance
    """
    global _conversation_client
    if _conversation_client is None:
        _conversation_client = ConversationClient(config)
    return _conversation_client
