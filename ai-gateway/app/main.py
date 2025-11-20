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
from pythonjsonlogger import jsonlogger

from app.models import Config
from app.routers import gateway


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

    yield

    # Shutdown
    logger.info("AI Gateway shutting down")


# Create FastAPI application
app = FastAPI(
    title="AI Gateway",
    description="AI Planning Pipeline for Home Assistant using Ollama",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(gateway.router, tags=["gateway"])


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
