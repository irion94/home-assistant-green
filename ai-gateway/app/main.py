"""AI Gateway FastAPI application.

Main entry point for the AI Planning Pipeline for Home Assistant.
Provides natural language interface to Home Assistant via Ollama LLM.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.models import Config
from app.routers import ask, voice, conversation, memory, session, tools
from app.services.database import db_service
from app.services.embeddings import embedding_service


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create JSON formatter
    formatter = jsonlogger.JsonFormatter(  # type: ignore[attr-defined]
        "%(asctime)s %(name)s %(levelname)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )

    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    config = Config()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("AI Gateway starting up")
    logger.info(f"Home Assistant URL: {config.ha_base_url}")
    logger.info(f"LLM Provider: {config.llm_provider}")
    if config.llm_provider.lower() == "openai":
        logger.info(f"OpenAI Model: {config.openai_model}")
    else:
        logger.info(f"Ollama URL: {config.ollama_base_url}")
        logger.info(f"Ollama Model: {config.ollama_model}")
    logger.info(f"STT Provider: {config.stt_provider}")
    if config.stt_provider.lower() == "whisper":
        logger.info(f"Whisper Model: {config.whisper_model}")

    # Connect to database (if enabled via feature flag)
    import os
    if os.getenv("DATABASE_ENABLED", "false").lower() == "true":
        try:
            await db_service.connect()
            logger.info("Database connected successfully")
        except Exception as e:
            logger.warning(f"Database connection failed: {e}. Memory features disabled.")
    else:
        logger.info("Database disabled (DATABASE_ENABLED=false)")

    # Register new tool architecture (if enabled via feature flag - Phase 2)
    if os.getenv("NEW_TOOLS_ENABLED", "false").lower() == "true":
        from app.services.tools.registry import tool_registry
        from app.services.tools.web_search_tool import WebSearchTool
        from app.services.tools.control_light_tool import ControlLightTool
        from app.services.tools.time_tool import GetTimeTool
        from app.services.tools.home_data_tool import GetHomeDataTool
        from app.services.tools.entity_tool import GetEntityTool
        from app.services.ha_client import HomeAssistantClient

        # Initialize HA client for tools
        ha_client = HomeAssistantClient(config)

        # Register all tools
        tool_registry.register(WebSearchTool())
        tool_registry.register(ControlLightTool(ha_client))
        tool_registry.register(GetTimeTool())
        tool_registry.register(GetHomeDataTool(ha_client))
        tool_registry.register(GetEntityTool(ha_client))

        logger.info(f"New tool architecture enabled: {len(tool_registry)} tools registered")
        logger.info(f"Registered tools: {', '.join(tool_registry.list_tools())}")
    else:
        logger.info("Using legacy tool architecture (NEW_TOOLS_ENABLED=false)")

    # Initialize learning systems (if enabled via feature flag - Phase 3)
    if os.getenv("LEARNING_ENABLED", "false").lower() == "true":
        if db_service.pool:
            from app.services.learning.context_engine import ContextEngine
            from app.services.learning.intent_analyzer import IntentAnalyzer
            from app.services.learning.suggestion_engine import SuggestionEngine

            # Store learning services in app state for access by routers
            app.state.context_engine = ContextEngine(db_service)
            app.state.intent_analyzer = IntentAnalyzer()
            app.state.suggestion_engine = SuggestionEngine(db_service)

            logger.info("Learning systems enabled: ContextEngine, IntentAnalyzer, SuggestionEngine")
        else:
            logger.warning("Learning systems require database. Enable DATABASE_ENABLED=true first.")
    else:
        logger.info("Learning systems disabled (LEARNING_ENABLED=false)")

    yield

    # Shutdown
    logger.info("AI Gateway shutting down")

    # Close database connection
    await db_service.disconnect()
    await embedding_service.close()
    logger.info("Database disconnected")


# Create FastAPI application
app = FastAPI(
    title="AI Gateway",
    description="AI Planning Pipeline for Home Assistant using Ollama",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for React Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.31:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ask.router, tags=["ask"])
app.include_router(voice.router, tags=["voice"])
app.include_router(conversation.router, tags=["conversation"])
app.include_router(memory.router)
app.include_router(session.router)
app.include_router(tools.router, tags=["tools"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        Welcome message with API info
    """
    return {
        "message": "AI Gateway for Home Assistant",
        "version": "0.1.0",
        "docs": "/docs",
    }
