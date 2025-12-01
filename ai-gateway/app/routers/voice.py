"""API router for voice endpoints.

This module implements the /voice, /voice/stream, and /health endpoints
that handle audio input and streaming responses.
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.models import AskResponse
from app.services.conversation_client import ConversationClient
from app.services.ha_client import HomeAssistantClient
from app.services.intent_matcher import IntentMatcher
from app.services.llm_client import LLMClient
from app.services.pipeline import STTPipeline
from app.services.web_search import get_web_search_client

from app.routers.dependencies import (
    get_conversation_client_dependency,
    get_ha_client,
    get_intent_matcher_dependency,
    get_llm_client_dependency,
    get_stt_pipeline_dependency,
    is_valid_input,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/voice", response_model=AskResponse)
async def voice(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    stt_pipeline: STTPipeline = Depends(get_stt_pipeline_dependency),
    intent_matcher: IntentMatcher = Depends(get_intent_matcher_dependency),
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
) -> AskResponse:
    """Process voice command audio and execute Home Assistant action.

    Flow:
    1. Receive audio file (WAV format)
    2. Transcribe audio to text using STT pipeline
    3. Send to LLM for translation to HA action plan
    4. Validate the plan
    5. Execute via Home Assistant REST API
    6. Return result

    Args:
        audio: Audio file upload
        stt_pipeline: STT pipeline for transcription
        intent_matcher: Fast pattern matcher
        llm_client: LLM client instance
        ha_client: Home Assistant client instance
        conversation_client: Conversation client for AI fallback

    Returns:
        Response with execution status and results

    Raises:
        HTTPException: If processing fails at any stage
    """
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
                ai_response = await conversation_client.chat(text, "voice_fallback")
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
    intent_matcher: IntentMatcher = Depends(get_intent_matcher_dependency),
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

            # Handle web search
            if action and action.action == "web_search":
                search_query = action.data.get("query", "")
                logger.info(f"[{correlation_id}] Web search: '{search_query}'")

                web_search_client = get_web_search_client()
                if not web_search_client.is_available():
                    yield f"data: {json.dumps({'sentence': 'Wyszukiwanie internetowe nie jest skonfigurowane', 'index': 0})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # Perform search
                search_result = await web_search_client.search(search_query)

                if not search_result.get("success"):
                    error_msg = search_result.get("error", "Unknown")
                    yield f"data: {json.dumps({'sentence': f'Błąd wyszukiwania: {error_msg}', 'index': 0})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                if not search_result.get("results"):
                    yield f"data: {json.dumps({'sentence': f'Nie znaleziono wyników dla: {search_query}', 'index': 0})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                # Format results for LLM
                search_context = web_search_client.format_for_llm(search_result)

                # Ask LLM to summarize results
                search_prompt = f"""Based on the following web search results, provide a concise summary for the user.
Answer in the same language as the search query.

{search_context}

User's question: {search_query}

Provide a helpful, concise summary (2-4 sentences). If the results don't fully answer the question, mention that."""

                # Stream LLM summary
                sentence_index = 0
                async for sentence in conversation_client.chat_stream_sentences(search_prompt, "web_search"):
                    yield f"data: {json.dumps({'sentence': sentence, 'index': sentence_index})}\n\n"
                    sentence_index += 1

                yield "data: [DONE]\n\n"
                logger.info(f"[{correlation_id}] Web search complete: {sentence_index} sentences")
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
