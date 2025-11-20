"""API router for AI Gateway endpoints.

This module implements the main /ask endpoint that orchestrates
the natural language → plan → execution pipeline.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.models import AskRequest, AskResponse, Config
from app.services.ha_client import HomeAssistantClient
from app.services.llm_client import LLMClient, get_llm_client
from app.services.whisper_client import WhisperClient, get_whisper_client

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
    llm_client: LLMClient = Depends(get_llm_client_dependency),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> AskResponse:
    """Process natural language command and execute Home Assistant action.

    Flow:
    1. Receive natural language command
    2. Send to Ollama for translation to HA action plan
    3. Validate the plan
    4. Execute via Home Assistant REST API
    5. Return result

    Args:
        request: Natural language command request
        ollama_client: Ollama client instance
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
        # Step 1: Translate command to action plan
        action = await llm_client.translate_command(request.text)

        if not action:
            logger.warning(f"[{correlation_id}] Failed to translate command")
            return AskResponse(
                status="error",
                message="Failed to translate command to action plan",
            )

        # Step 2: Handle "none" action (unsupported/unknown command)
        if action.action == "none":
            logger.info(f"[{correlation_id}] Command not supported: {request.text}")
            return AskResponse(
                status="success",
                plan=action,
                message="Command understood but no action available",
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


@router.post("/voice", response_model=AskResponse)
async def voice(
    audio: UploadFile = File(..., description="Audio file in WAV format"),
    whisper_client: WhisperClient = Depends(get_whisper_client),
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
            text = await whisper_client.transcribe(audio_bytes)
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

        # Step 3: Translate command to action plan
        action = await llm_client.translate_command(text)

        if not action:
            logger.warning(f"[{correlation_id}] Failed to translate command")
            return AskResponse(
                status="error",
                message="Failed to translate command to action plan",
            )

        # Step 4: Handle "none" action (unsupported/unknown command)
        if action.action == "none":
            logger.info(f"[{correlation_id}] Command not supported: {text}")
            return AskResponse(
                status="success",
                plan=action,
                message=f"Understood: '{text}' but no action available",
            )

        # Step 5: Execute service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Failed to execute Home Assistant service call",
            )

        # Step 6: Success!
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
