"""Shared dependencies for API routers.

This module contains FastAPI dependency injection functions
used across multiple routers.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.models import Config
from app.services.conversation_client import ConversationClient, get_conversation_client
from app.services.database import db_service
from app.services.entity_discovery import EntityDiscovery, get_entity_discovery
from app.services.ha_client import HomeAssistantClient
from app.services.intent_matcher import IntentMatcher, get_intent_matcher
from app.services.llm_cache import LLMCache, get_llm_cache
from app.services.llm_client import LLMClient, get_llm_client
from app.services.pattern_learner import PatternLearner, get_pattern_learner
from app.services.pipeline import STTPipeline
from app.services.stt_client import STTClient, get_stt_client, get_stt_pipeline


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


def get_stt_client_dependency(config: Config = Depends(get_config)) -> STTClient:
    """Dependency to get STT client (Whisper or Vosk).

    Args:
        config: Application configuration

    Returns:
        Initialized STT client based on configuration
    """
    return get_stt_client(config)


def get_stt_pipeline_dependency(config: Config = Depends(get_config)) -> STTPipeline:
    """Dependency to get STT pipeline with tiered recognition.

    Args:
        config: Application configuration

    Returns:
        Initialized STT pipeline
    """
    return get_stt_pipeline(config)


def get_conversation_client_dependency(config: Config = Depends(get_config)) -> ConversationClient:
    """Dependency to get conversation client with database persistence.

    Args:
        config: Application configuration

    Returns:
        Initialized conversation client with db_service for persistence
    """
    # Pass db_service only if connected (pool is not None)
    db = db_service if db_service.pool is not None else None
    return get_conversation_client(config, db)


def get_intent_matcher_dependency() -> IntentMatcher:
    """Dependency to get intent matcher.

    Returns:
        IntentMatcher singleton instance
    """
    return get_intent_matcher()


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


# Phase 3: Learning Systems Dependencies

def get_context_engine(request: Request):
    """Dependency to get context engine from app state (Phase 3).

    Returns None if learning systems are disabled.

    Args:
        request: FastAPI request object

    Returns:
        ContextEngine instance or None
    """
    return getattr(request.app.state, "context_engine", None)


def get_intent_analyzer(request: Request):
    """Dependency to get intent analyzer from app state (Phase 3).

    Returns None if learning systems are disabled.

    Args:
        request: FastAPI request object

    Returns:
        IntentAnalyzer instance or None
    """
    return getattr(request.app.state, "intent_analyzer", None)


def get_suggestion_engine(request: Request):
    """Dependency to get suggestion engine from app state (Phase 3).

    Returns None if learning systems are disabled.

    Args:
        request: FastAPI request object

    Returns:
        SuggestionEngine instance or None
    """
    return getattr(request.app.state, "suggestion_engine", None)
