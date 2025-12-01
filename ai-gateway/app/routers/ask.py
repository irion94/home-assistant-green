"""API router for /ask endpoint.

This module implements the /ask endpoint that processes text commands
and executes Home Assistant actions.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.models import AskRequest, AskResponse, Config
from app.services.entity_discovery import EntityDiscovery
from app.services.ha_client import HomeAssistantClient
from app.services.intent_matcher import IntentMatcher
from app.services.llm_cache import LLMCache
from app.services.llm_client import LLMClient
from app.services.pattern_learner import PatternLearner
from app.services.pipeline import IntentPipeline

from app.routers.dependencies import (
    get_config,
    get_entity_discovery_dependency,
    get_ha_client,
    get_llm_cache_dependency,
    get_llm_client_dependency,
    get_pattern_learner_dependency,
    get_intent_matcher_dependency,
    is_valid_input,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    config: Config = Depends(get_config),
    intent_matcher: IntentMatcher = Depends(get_intent_matcher_dependency),
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
            confidence_threshold=config.intent_confidence_threshold,
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

        # Handle special actions - fall back to AI for questions
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

        # Handle scene creation (multiple actions)
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

        # Execute single service call
        ha_response = await ha_client.call_service(action)

        if ha_response is None:
            logger.error(f"[{correlation_id}] Failed to execute HA service call")
            return AskResponse(
                status="error",
                plan=action,
                message="Nie udało się wykonać polecenia",
            )

        # Success!
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
