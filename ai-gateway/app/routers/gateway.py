"""API router for AI Gateway endpoints.

This module implements the main /ask endpoint that orchestrates
the natural language → plan → execution pipeline.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from pydantic import BaseModel, Field

from app.models import AskRequest, AskResponse, Config
from app.services.conversation_client import ConversationClient, get_conversation_client
from app.services.ha_client import HomeAssistantClient
from app.services.intent_matcher import IntentMatcher, get_intent_matcher
from app.services.llm_client import LLMClient, get_llm_client
from app.services.stt_client import STTClient, get_stt_client


class ConversationRequest(BaseModel):
    """Request schema for /conversation endpoint."""
    text: str = Field(..., description="User message text")
    session_id: str = Field(..., description="Conversation session ID")
    end_session: bool = Field(default=False, description="End the conversation session")


class ConversationResponse(BaseModel):
    """Response schema for /conversation endpoint."""
    status: str = Field(..., description="Request status")
    text: str | None = Field(None, description="AI response text")
    session_id: str = Field(..., description="Session ID")
    message: str | None = Field(None, description="Status message")

logger = logging.getLogger(__name__)
router = APIRouter()


def get_config() -> Config:
    """Dependency to get application configuration.

    Returns:
        Loaded configuration
    """
    return Config()


def get_llm_client_dependency(config: Config = Depends(get_config)) -> LLMClient:
    """Dependency to get LLM client (Ollama or OpenAI).

    Args:
        config: Application configuration

    Returns:
        Initialized LLM client based on configuration
    """
    return get_llm_client(config)


def get_ha_client(config: Config = Depends(get_config)) -> HomeAssistantClient:
    """Dependency to get Home Assistant client.

    Args:
        config: Application configuration

    Returns:
        Initialized HA client
    """
    return HomeAssistantClient(config)


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    intent_matcher: IntentMatcher = Depends(get_intent_matcher),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> AskResponse:
    """Process natural language command and execute Home Assistant action.

    Flow:
    1. Receive natural language command
    2. Try fast pattern matching first
    3. Fall back to LLM if no match
    4. Execute via Home Assistant REST API
    5. Return result

    Args:
        request: Natural language command request
        intent_matcher: Fast pattern matcher instance
        llm_client: LLM client instance (Ollama or OpenAI)
        ha_client: Home Assistant client instance

    Returns:
        Response with execution status and results

    Raises:
        HTTPException: If processing fails at any stage
    """
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Processing request: {request.text}")

    try:
        # Step 1: Try fast pattern matching first
        action = intent_matcher.match(request.text)
        if action:
            logger.info(f"[{correlation_id}] Fast path: matched via pattern")
        else:
            # Step 2: Fall back to LLM for complex commands
            logger.info(f"[{correlation_id}] Slow path: using LLM")
            action = await llm_client.translate_command(request.text)

        if not action:
            logger.warning(f"[{correlation_id}] Failed to translate command")
            return AskResponse(
                status="error",
                message="Failed to translate command to action plan",
            )

        # Step 2: Handle special actions
        if action.action == "none":
            logger.info(f"[{correlation_id}] Command not supported: {request.text}")
            return AskResponse(
                status="success",
                plan=action,
                message="Command understood but no action available",
            )

        if action.action == "conversation_start":
            logger.info(f"[{correlation_id}] Conversation mode requested")
            return AskResponse(
                status="success",
                plan=action,
                message="Conversation mode started",
            )

        if action.action == "conversation_end":
            logger.info(f"[{correlation_id}] Conversation mode ended")
            return AskResponse(
                status="success",
                plan=action,
                message="Conversation mode ended",
            )

        # Step 3: Execute service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Failed to execute Home Assistant service call",
            )

        # Step 4: Success!
        logger.info(f"[{correlation_id}] Successfully executed action")
        return AskResponse(
            status="success",
            plan=action,
            message="Action executed successfully",
            ha_response=ha_response,
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


def get_stt_client_dependency(config: Config = Depends(get_config)) -> STTClient:
    """Dependency to get STT client (Whisper or Vosk).

    Args:
        config: Application configuration

    Returns:
        Initialized STT client based on configuration
    """
    return get_stt_client(config)


@router.post("/voice", response_model=AskResponse)
async def voice(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    stt_client: STTClient = Depends(get_stt_client_dependency),
    intent_matcher: IntentMatcher = Depends(get_intent_matcher),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> AskResponse:
    """Process voice command audio and execute Home Assistant action.

    Flow:
    1. Receive audio file (WAV format)
    2. Transcribe audio to text using Whisper
    3. Send to Ollama for translation to HA action plan
    4. Validate the plan
    5. Execute via Home Assistant REST API
    6. Return result

    Args:
        audio: Audio file upload
        whisper_client: Whisper transcription client
        ollama_client: Ollama client instance
        ha_client: Home Assistant client instance

    Returns:
        Response with execution status and results

    Raises:
        HTTPException: If processing fails at any stage
    """
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Received voice command: {audio.filename}")

    try:
        # Step 1: Read audio file
        audio_bytes = await audio.read()
        logger.info(f"[{correlation_id}] Audio size: {len(audio_bytes)} bytes")

        # Step 2: Transcribe audio to text
        try:
            text = await stt_client.transcribe(audio_bytes)
        except Exception as e:
            logger.error(f"[{correlation_id}] Transcription failed: {e}")
            return AskResponse(
                status="error",
                message=f"Failed to transcribe audio: {e}",
            )

        if not text or not text.strip():
            logger.warning(f"[{correlation_id}] Empty transcription")
            return AskResponse(
                status="error",
                message="Could not understand audio - no speech detected",
            )

        logger.info(f"[{correlation_id}] Transcribed text: {text}")

        # Step 3: Try fast pattern matching first
        action = intent_matcher.match(text)
        if action:
            logger.info(f"[{correlation_id}] Fast path: matched via pattern")
        else:
            # Step 4: Fall back to LLM for complex commands
            logger.info(f"[{correlation_id}] Slow path: using LLM")
            action = await llm_client.translate_command(text)

        if not action:
            logger.warning(f"[{correlation_id}] Failed to translate command")
            return AskResponse(
                status="error",
                message="Failed to translate command to action plan",
            )

        # Step 5: Handle special actions
        if action.action == "none":
            logger.info(f"[{correlation_id}] Command not supported: {text}")
            return AskResponse(
                status="success",
                plan=action,
                message=f"Understood: '{text}' but no action available",
            )

        if action.action == "conversation_start":
            logger.info(f"[{correlation_id}] Conversation mode requested via voice")
            return AskResponse(
                status="success",
                plan=action,
                message="Conversation mode started",
            )

        if action.action == "conversation_end":
            logger.info(f"[{correlation_id}] Conversation mode ended via voice")
            return AskResponse(
                status="success",
                plan=action,
                message="Conversation mode ended",
            )

        # Step 6: Execute service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Failed to execute Home Assistant service call",
            )

        # Step 7: Success!
        logger.info(f"[{correlation_id}] Successfully executed action from voice command")
        return AskResponse(
            status="success",
            plan=action,
            message=f"Action executed successfully for: '{text}'",
            ha_response=ha_response,
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/health")
async def health(ha_client: HomeAssistantClient = Depends(get_ha_client)) -> dict[str, str]:
    """Health check endpoint.

    Verifies that:
    1. API gateway is running
    2. Home Assistant is accessible

    Args:
        ha_client: Home Assistant client instance

    Returns:
        Health status dictionary

    Raises:
        HTTPException: If health check fails
    """
    # Check HA connectivity
    ha_ok = await ha_client.health_check()

    if not ha_ok:
        raise HTTPException(status_code=503, detail="Home Assistant not accessible")

    return {
        "status": "healthy",
        "home_assistant": "connected",
    }


def get_conversation_client_dependency(config: Config = Depends(get_config)) -> ConversationClient:
    """Dependency to get conversation client.

    Args:
        config: Application configuration

    Returns:
        Initialized conversation client
    """
    return get_conversation_client(config)


@router.post("/conversation", response_model=ConversationResponse)
async def conversation(
    request: ConversationRequest,
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> ConversationResponse:
    """Process conversation message and return AI response.

    Args:
        request: Conversation request with text and session_id
        conversation_client: Conversation client instance
        ha_client: Home Assistant client for TTS

    Returns:
        ConversationResponse with AI response text
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Conversation request: session={request.session_id}")

    try:
        # Handle session end
        if request.end_session:
            conversation_client.clear_session(request.session_id)
            return ConversationResponse(
                status="success",
                text=None,
                session_id=request.session_id,
                message="Conversation ended",
            )

        # Get AI response
        response_text = await conversation_client.chat(request.text, request.session_id)

        logger.info(f"[{correlation_id}] Conversation response: {len(response_text)} chars")

        # Send response to TTS (Nest Hub) with faster speed
        try:
            from app.models import HAAction

            # Detect language - check for Polish characters
            polish_chars = set('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')
            is_polish = any(char in polish_chars for char in response_text)
            language = "pl" if is_polish else "en"

            tts_action = HAAction(
                action="call_service",
                service="tts.speak",
                entity_id="tts.google_translate_en_com",
                data={
                    "media_player_entity_id": "media_player.living_room_display",
                    "message": response_text,
                    "language": language,
                    "options": {
                        "speed": 1.2,  # 20% faster
                    },
                },
            )
            await ha_client.call_service(tts_action)
            logger.info(f"[{correlation_id}] TTS sent to Nest Hub (language={language}, speed=1.2)")
        except Exception as e:
            logger.warning(f"[{correlation_id}] TTS failed: {e}")

        return ConversationResponse(
            status="success",
            text=response_text,
            session_id=request.session_id,
            message="Response generated",
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Conversation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversation error: {e}")


@router.post("/conversation/voice", response_model=ConversationResponse)
async def conversation_voice(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    session_id: str = "default",
    stt_client: STTClient = Depends(get_stt_client_dependency),
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> ConversationResponse:
    """Process voice input for conversation mode.

    Args:
        audio: Audio file upload
        session_id: Conversation session ID
        stt_client: STT client for transcription
        conversation_client: Conversation client
        ha_client: Home Assistant client for TTS

    Returns:
        ConversationResponse with AI response text
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Conversation voice: session={session_id}")

    try:
        # Transcribe audio
        audio_bytes = await audio.read()
        text = await stt_client.transcribe(audio_bytes)

        if not text or not text.strip():
            return ConversationResponse(
                status="error",
                text=None,
                session_id=session_id,
                message="Could not understand audio",
            )

        logger.info(f"[{correlation_id}] Transcribed: {text}")

        # Get AI response
        response_text = await conversation_client.chat(text, session_id)

        # Show transcription on display
        try:
            from app.models import HAAction

            # Send notification with transcribed text to Nest Hub
            notify_action = HAAction(
                action="call_service",
                service="notify.mobile_app_living_room_display",
                entity_id=None,
                data={
                    "message": f"🎤 {text}",
                    "title": "You said:",
                },
            )
            await ha_client.call_service(notify_action)
        except Exception as e:
            logger.debug(f"[{correlation_id}] Display notification failed: {e}")

        # Send to TTS with faster speed
        try:
            from app.models import HAAction

            # Detect language - check for Polish characters
            polish_chars = set('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')
            is_polish = any(char in polish_chars for char in response_text)
            language = "pl" if is_polish else "en"

            tts_action = HAAction(
                action="call_service",
                service="tts.speak",
                entity_id="tts.google_translate_en_com",
                data={
                    "media_player_entity_id": "media_player.living_room_display",
                    "message": response_text,
                    "language": language,
                    "options": {
                        "speed": 1.2,  # 20% faster
                    },
                },
            )
            await ha_client.call_service(tts_action)
            logger.info(f"[{correlation_id}] TTS sent (language={language}, speed=1.2)")
        except Exception as e:
            logger.warning(f"[{correlation_id}] TTS failed: {e}")

        return ConversationResponse(
            status="success",
            text=response_text,
            session_id=session_id,
            message=f"Response to: '{text}'",
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Conversation voice error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversation error: {e}")
