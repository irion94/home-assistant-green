"""API router for conversation endpoints.

This module implements the /conversation and /conversation/voice endpoints
for multi-turn AI conversations with function calling support.
"""

from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models import HAAction
from app.services.conversation_client import ConversationClient
from app.services.ha_client import HomeAssistantClient
from app.services.stt_client import STTClient

from app.routers.dependencies import (
    get_conversation_client_dependency,
    get_ha_client,
    get_stt_client_dependency,
)
from app.utils.text import detect_language

logger = logging.getLogger(__name__)
router = APIRouter()


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
    transcription: str | None = Field(None, description="Transcribed user speech (voice only)")


class Message(BaseModel):
    """Message schema for streaming chat (Vercel AI SDK format)."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for /conversation/stream endpoint (Vercel AI SDK format)."""
    messages: list[Message] = Field(..., description="Conversation message history")
    session_id: str = Field(default="default", description="Conversation session ID")


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

        # Get AI response with function calling (LLM decides when to use tools)
        response_text = await conversation_client.chat(request.text, request.session_id)

        logger.info(f"[{correlation_id}] Conversation response: {len(response_text)} chars")

        # Send response to TTS (Nest Hub) with faster speed
        try:
            language = detect_language(response_text)

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

        # Get AI response with function calling (LLM decides when to use tools)
        response_text = await conversation_client.chat(text, session_id)

        # Show transcription on display
        try:
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
            language = detect_language(response_text)

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
            transcription=text,
        )

    except Exception as e:
        logger.error(f"[{correlation_id}] Conversation voice error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversation error: {e}")


@router.post("/conversation/stream")
async def conversation_stream(
    request: ChatRequest,
    conversation_client: ConversationClient = Depends(get_conversation_client_dependency),
) -> StreamingResponse:
    """Stream AI response using Server-Sent Events (SSE) - Vercel AI SDK compatible.

    This endpoint accepts a conversation history in Vercel AI SDK format and streams
    the AI response token-by-token for real-time display in the UI.

    Args:
        request: Chat request with message history and session ID
        conversation_client: Conversation client instance

    Returns:
        StreamingResponse with SSE events containing response tokens

    Example Request:
        POST /conversation/stream
        {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ],
            "session_id": "chat_123"
        }

    Example Response (SSE):
        data: {"content": "I'm"}
        data: {"content": " doing"}
        data: {"content": " well"}
        data: [DONE]
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        f"[{correlation_id}] Stream request: session={request.session_id}, "
        f"messages={len(request.messages)}"
    )

    # Extract the last user message from the conversation history
    user_message = next(
        (msg.content for msg in reversed(request.messages) if msg.role == "user"),
        None,
    )

    if not user_message:
        async def error_stream():
            yield f"data: {json.dumps({'error': 'No user message found'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def generate():
        """Generate SSE stream of response tokens."""
        try:
            logger.info(f"[{correlation_id}] Streaming response for: '{user_message[:50]}...'")

            # Stream response token by token using existing chat_stream method
            token_count = 0
            async for token in conversation_client.chat_stream(user_message, request.session_id):
                # Vercel AI SDK format: {"content": "token"}
                yield f"data: {json.dumps({'content': token})}\n\n"
                token_count += 1

            logger.info(f"[{correlation_id}] Stream complete: {token_count} tokens")

            # Signal completion (Vercel AI SDK expects this)
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[{correlation_id}] Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
