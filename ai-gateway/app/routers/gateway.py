"""API router for AI Gateway endpoints.

This module implements the main /ask endpoint that orchestrates
the natural language → plan → execution pipeline.
"""

from __future__ import annotations

import logging
import uuid

import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from app.models import AskRequest, AskResponse, Config
from app.services.conversation_client import ConversationClient, get_conversation_client
from app.services.entity_discovery import EntityDiscovery, get_entity_discovery
from app.services.ha_client import HomeAssistantClient
from app.services.intent_matcher import IntentMatcher, get_intent_matcher
from app.services.llm_cache import LLMCache, get_llm_cache
from app.services.llm_client import LLMClient, get_llm_client
from app.services.pattern_learner import PatternLearner, get_pattern_learner
from app.services.pipeline import IntentPipeline, IntentResult, STTPipeline
from app.services.stt_client import STTClient, get_stt_client, get_stt_pipeline


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


def is_valid_input(text: str) -> bool:
    """Check if text is meaningful enough for AI processing.

    Filters out gibberish, noise, and invalid transcriptions before
    sending to AI fallback. Returns False for:
    - Less than 2 words
    - Only single-character words (noise)

    Args:
        text: Transcribed text to validate

    Returns:
        True if text is valid for AI processing
    """
    words = text.split()
    if len(words) < 2:
        return False
    # Check for actual words (not just noise like "a b c")
    if all(len(w) <= 2 for w in words):
        return False
    return True


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


def get_entity_discovery_dependency(
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> EntityDiscovery:
    """Dependency to get entity discovery service.

    Args:
        ha_client: Home Assistant client

    Returns:
        EntityDiscovery service instance
    """
    return get_entity_discovery(ha_client)


def get_llm_cache_dependency() -> LLMCache:
    """Dependency to get LLM cache.

    Returns:
        LLMCache singleton instance
    """
    return get_llm_cache()


def get_pattern_learner_dependency() -> PatternLearner:
    """Dependency to get pattern learner.

    Returns:
        PatternLearner singleton instance
    """
    return get_pattern_learner()


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    intent_matcher: IntentMatcher = Depends(get_intent_matcher),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    entity_discovery: EntityDiscovery = Depends(get_entity_discovery_dependency),
    llm_cache: LLMCache = Depends(get_llm_cache_dependency),
    pattern_learner: PatternLearner = Depends(get_pattern_learner_dependency),
) -> AskResponse:
    """Process natural language command and execute Home Assistant action.

    Flow:
    1. Receive natural language command
    2. Run pipeline (pattern matcher + LLM in parallel)
    3. Use first confident result
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
        # Create and run intent pipeline with dynamic entity discovery and optimizations
        pipeline = IntentPipeline(
            intent_matcher=intent_matcher,
            llm_client=llm_client,
            confidence_threshold=0.8,
            entity_discovery=entity_discovery,
            llm_cache=llm_cache,
            pattern_learner=pattern_learner,
        )
        result = await pipeline.process(request.text)

        action = result.action
        logger.info(
            f"[{correlation_id}] Pipeline result: source={result.source}, "
            f"confidence={result.confidence:.2f}, latency={result.latency_ms:.0f}ms"
        )

        if not action:
            logger.warning(f"[{correlation_id}] Failed to translate command")
            return AskResponse(
                status="error",
                message="Nie udało się przetłumaczyć polecenia",
            )

        # Step 2: Handle special actions - fall back to AI for questions
        if action.action == "none":
            # Validate input before sending to AI
            if not is_valid_input(request.text):
                logger.info(f"[{correlation_id}] Invalid input for AI fallback: '{request.text}'")
                return AskResponse(
                    status="success",
                    plan=None,
                    message="Nie rozumiem",
                )

            logger.info(f"[{correlation_id}] No HA action - falling back to AI conversation")
            try:
                # Import conversation client here to avoid circular imports
                from app.services.conversation_client import get_conversation_client
                conv_client = get_conversation_client(Config())
                ai_response = await conv_client.chat(request.text, "ask_fallback")
                logger.info(f"[{correlation_id}] AI fallback response: {len(ai_response)} chars")
                return AskResponse(
                    status="success",
                    plan=None,
                    message=ai_response,
                    text=ai_response,
                )
            except Exception as e:
                logger.error(f"[{correlation_id}] AI fallback failed: {e}")
                return AskResponse(
                    status="success",
                    plan=action,
                    message="Polecenie zrozumiane, ale brak dostępnej akcji",
                )

        if action.action == "conversation_start":
            logger.info(f"[{correlation_id}] Conversation mode requested")
            return AskResponse(
                status="success",
                plan=action,
                message="Tryb rozmowy rozpoczęty",
            )

        if action.action == "conversation_end":
            logger.info(f"[{correlation_id}] Conversation mode ended")
            return AskResponse(
                status="success",
                plan=action,
                message="Tryb rozmowy zakończony",
            )

        # Step 3: Handle scene creation (multiple actions)
        if action.action == "create_scene":
            if not action.actions:
                logger.warning(f"[{correlation_id}] create_scene with no actions")
                return AskResponse(
                    status="error",
                    plan=action,
                    message="Scena nie zawiera żadnych akcji",
                )

            logger.info(f"[{correlation_id}] Executing scene with {len(action.actions)} actions")
            scene_results = await ha_client.call_services(action.actions)

            # Check if any actions succeeded
            success_count = sum(1 for r in scene_results if r["status"] == "success")
            if success_count == 0:
                logger.error(f"[{correlation_id}] All scene actions failed")
                return AskResponse(
                    status="error",
                    plan=action,
                    message="Nie udało się wykonać sceny",
                    ha_response=scene_results,
                )

            logger.info(f"[{correlation_id}] Scene executed: {success_count}/{len(action.actions)} succeeded")
            return AskResponse(
                status="success",
                plan=action,
                message=f"Gotowe ({success_count}/{len(action.actions)} akcji)",
                ha_response=scene_results,
            )

        # Step 4: Execute single service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Nie udało się wykonać polecenia",
            )

        # Step 4: Success!
        logger.info(f"[{correlation_id}] Successfully executed action")
        return AskResponse(
            status="success",
            plan=action,
            message="Gotowe",
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


def get_stt_pipeline_dependency(config: Config = Depends(get_config)) -> STTPipeline:
    """Dependency to get STT pipeline (Vosk -> Whisper).

    Args:
        config: Application configuration

    Returns:
        Initialized STT pipeline
    """
    return get_stt_pipeline(config)


def get_conversation_client_dependency(config: Config = Depends(get_config)) -> ConversationClient:
    """Dependency to get conversation client.

    Args:
        config: Application configuration

    Returns:
        Initialized conversation client
    """
    return get_conversation_client(config)


@router.post("/voice", response_model=AskResponse)
async def voice(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    stt_pipeline: STTPipeline = Depends(get_stt_pipeline_dependency),
    intent_matcher: IntentMatcher = Depends(get_intent_matcher),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
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

        # Step 2: Transcribe audio using STT pipeline (Vosk -> Whisper)
        try:
            stt_result = await stt_pipeline.transcribe(audio_bytes)
            text = stt_result.text
            logger.info(
                f"[{correlation_id}] STT result: source={stt_result.source}, "
                f"confidence={stt_result.confidence:.2f}, latency={stt_result.latency_ms:.0f}ms"
            )
        except Exception as e:
            logger.error(f"[{correlation_id}] Transcription failed: {e}")
            return AskResponse(
                status="error",
                message=f"Błąd transkrypcji: {e}",
            )

        if not text or not text.strip():
            logger.warning(f"[{correlation_id}] Empty transcription")
            return AskResponse(
                status="error",
                message="Nie wykryto mowy",
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
                message="Nie udało się przetłumaczyć polecenia",
            )

        # Step 5: Handle special actions - fall back to AI for questions
        if action.action == "none":
            # Validate input before sending to AI
            if not is_valid_input(text):
                logger.info(f"[{correlation_id}] Invalid input for AI fallback: '{text}'")
                return AskResponse(
                    status="success",
                    plan=None,
                    message="Nie rozumiem",
                )

            logger.info(f"[{correlation_id}] No HA action - falling back to AI conversation")
            try:
                # Treat as a question and get AI response
                ai_response = await conversation_client.chat(text, "voice_fallback")
                logger.info(f"[{correlation_id}] AI fallback response: {len(ai_response)} chars")
                return AskResponse(
                    status="success",
                    plan=None,
                    message=ai_response,  # AI response for TTS
                    text=ai_response,  # Also in text field for clarity
                )
            except Exception as e:
                logger.error(f"[{correlation_id}] AI fallback failed: {e}")
                return AskResponse(
                    status="success",
                    plan=action,
                    message="Polecenie zrozumiane, ale brak dostępnej akcji",
                )

        if action.action == "conversation_start":
            logger.info(f"[{correlation_id}] Conversation mode requested via voice")
            return AskResponse(
                status="success",
                plan=action,
                message="Tryb rozmowy rozpoczęty",
            )

        if action.action == "conversation_end":
            logger.info(f"[{correlation_id}] Conversation mode ended via voice")
            return AskResponse(
                status="success",
                plan=action,
                message="Tryb rozmowy zakończony",
            )

        # Step 6: Execute service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Nie udało się wykonać polecenia",
            )

        # Step 7: Success!
        logger.info(f"[{correlation_id}] Successfully executed action from voice command")
        return AskResponse(
            status="success",
            plan=action,
            message="Gotowe",
            ha_response=ha_response,
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.post("/voice/stream")
async def voice_stream(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    stt_pipeline: STTPipeline = Depends(get_stt_pipeline_dependency),
    intent_matcher: IntentMatcher = Depends(get_intent_matcher),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
) -> StreamingResponse:
    """Process voice command and stream AI response sentence by sentence.

    Uses Server-Sent Events (SSE) to stream sentences as they become available,
    enabling the client to start TTS playback before the full response is ready.

    Flow:
    1. Receive audio file (WAV format)
    2. Transcribe audio to text
    3. Check for HA action first
    4. If no action, stream AI response sentence by sentence
    5. Client receives sentences via SSE for immediate TTS

    Args:
        audio: Audio file upload
        stt_pipeline: STT pipeline for transcription
        intent_matcher: Fast pattern matcher
        llm_client: LLM client for intent translation
        ha_client: Home Assistant client
        conversation_client: Conversation client for streaming

    Returns:
        StreamingResponse with SSE data
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] Streaming voice command: {audio.filename}")

    async def generate():
        try:
            # Step 1: Read and transcribe audio
            audio_bytes = await audio.read()
            logger.info(f"[{correlation_id}] Audio size: {len(audio_bytes)} bytes")

            try:
                stt_result = await stt_pipeline.transcribe(audio_bytes)
                text = stt_result.text
                logger.info(
                    f"[{correlation_id}] STT result: source={stt_result.source}, "
                    f"confidence={stt_result.confidence:.2f}"
                )
            except Exception as e:
                logger.error(f"[{correlation_id}] Transcription failed: {e}")
                yield f"data: {json.dumps({'error': f'Transcription failed: {e}'})}\n\n"
                return

            if not text or not text.strip():
                yield f"data: {json.dumps({'error': 'No speech detected'})}\n\n"
                return

            # Send transcribed text first
            yield f"data: {json.dumps({'transcription': text})}\n\n"

            # Step 2: Check for HA action
            action = intent_matcher.match(text)
            if not action:
                action = await llm_client.translate_command(text)

            # Step 3: Handle HA actions (non-streaming)
            if action and action.action not in ("none", "conversation_start", "conversation_end"):
                ha_response = await ha_client.call_service(action)
                if ha_response is not None:
                    yield f"data: {json.dumps({'sentence': 'Gotowe', 'index': 0, 'action': action.action})}\n\n"
                else:
                    yield f"data: {json.dumps({'sentence': 'Nie udało się wykonać polecenia', 'index': 0})}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Handle conversation mode triggers
            if action and action.action == "conversation_start":
                yield f"data: {json.dumps({'sentence': 'Tryb rozmowy rozpoczęty', 'index': 0, 'action': 'conversation_start'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            if action and action.action == "conversation_end":
                yield f"data: {json.dumps({'sentence': 'Tryb rozmowy zakończony', 'index': 0, 'action': 'conversation_end'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Step 4: Validate input for AI fallback
            if not is_valid_input(text):
                yield f"data: {json.dumps({'sentence': 'Nie rozumiem', 'index': 0})}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Step 5: Stream AI response sentence by sentence
            logger.info(f"[{correlation_id}] Streaming AI response...")
            sentence_index = 0
            async for sentence in conversation_client.chat_stream_sentences(text, "voice_stream"):
                yield f"data: {json.dumps({'sentence': sentence, 'index': sentence_index})}\n\n"
                sentence_index += 1

            yield "data: [DONE]\n\n"
            logger.info(f"[{correlation_id}] Streaming complete: {sentence_index} sentences")

        except Exception as e:
            logger.error(f"[{correlation_id}] Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


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
