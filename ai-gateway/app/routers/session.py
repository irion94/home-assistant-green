"""API router for session management endpoints.

This module provides REST API for managing conversation sessions,
including starting sessions, retrieving history, and listing recent sessions.

Part of Phase 3 of the Voice Assistant Architecture Redesign.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models import Config
from app.services.database import db_service
from app.services.conversation_client import (
    ConversationClient,
    get_conversation_client,
    _sessions,
)
from app.routers.dependencies import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["session"])


# ==========================================
# Request/Response Models
# ==========================================

class StartSessionRequest(BaseModel):
    """Request to start a new session."""
    room_id: str = Field(default="default", description="Room identifier")
    conversation_mode: bool = Field(
        default=False,
        description="True for multi-turn, False for single command"
    )


class StartSessionResponse(BaseModel):
    """Response with new session details."""
    session_id: str
    room_id: str
    conversation_mode: bool
    created_at: str


class SessionMessage(BaseModel):
    """A single message in a session."""
    id: int | None = None
    role: str
    content: str
    language: str | None = None
    intent: str | None = None
    created_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionHistoryResponse(BaseModel):
    """Response with session conversation history."""
    session_id: str
    messages: list[SessionMessage]
    message_count: int


class RecentSession(BaseModel):
    """Summary of a recent session."""
    session_id: str
    message_count: int
    started_at: str
    last_message_at: str


class RecentSessionsResponse(BaseModel):
    """Response with list of recent sessions."""
    sessions: list[RecentSession]
    total: int


class EndSessionResponse(BaseModel):
    """Response when ending a session."""
    session_id: str
    status: str
    message_count: int


# ==========================================
# Endpoints
# ==========================================

@router.post("/start", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
) -> StartSessionResponse:
    """Start a new conversation session.

    Creates a new session ID and optionally initializes it in the database.
    The session can be used for subsequent conversation messages.

    Args:
        request: Session configuration including room_id and mode

    Returns:
        Session details including the generated session_id
    """
    # Generate unique session ID with room prefix
    session_id = f"{request.room_id}_{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow().isoformat()

    logger.info(
        f"Starting new session: {session_id} "
        f"(room={request.room_id}, mode={'multi-turn' if request.conversation_mode else 'single'})"
    )

    return StartSessionResponse(
        session_id=session_id,
        room_id=request.room_id,
        conversation_mode=request.conversation_mode,
        created_at=created_at,
    )


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    limit: int = 50,
) -> SessionHistoryResponse:
    """Get conversation history for a session.

    Retrieves messages from both in-memory cache and database.
    Database is preferred for historical sessions.

    Args:
        session_id: The session identifier
        limit: Maximum number of messages to return

    Returns:
        Session history with messages
    """
    messages: list[SessionMessage] = []

    # First try in-memory cache (active sessions)
    if session_id in _sessions and _sessions[session_id]:
        for msg in _sessions[session_id][-limit:]:
            messages.append(SessionMessage(
                role=msg["role"],
                content=msg["content"],
            ))
        logger.debug(f"Retrieved {len(messages)} messages from memory for {session_id}")

    # If no in-memory messages, try database
    if not messages and db_service.pool is not None:
        try:
            history = await db_service.get_conversation_history(session_id, limit)
            for msg in history:
                messages.append(SessionMessage(
                    id=msg.get("id"),
                    role=msg["role"],
                    content=msg["content"],
                    language=msg.get("language"),
                    intent=msg.get("intent"),
                    created_at=msg.get("created_at"),
                    metadata=msg.get("metadata", {}),
                ))
            logger.debug(f"Retrieved {len(messages)} messages from DB for {session_id}")
        except Exception as e:
            logger.warning(f"Failed to retrieve history from DB: {e}")

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        message_count=len(messages),
    )


@router.get("s/recent", response_model=RecentSessionsResponse)
async def get_recent_sessions(
    limit: int = 20,
) -> RecentSessionsResponse:
    """Get list of recent conversation sessions.

    Retrieves session summaries from the database, including
    message counts and timestamps.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of recent sessions with summaries
    """
    sessions: list[RecentSession] = []

    if db_service.pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database not connected"
        )

    try:
        recent = await db_service.get_recent_sessions(limit)
        for sess in recent:
            sessions.append(RecentSession(
                session_id=sess["session_id"],
                message_count=sess["message_count"],
                started_at=sess["started_at"],
                last_message_at=sess["last_message_at"],
            ))
    except Exception as e:
        logger.error(f"Failed to retrieve recent sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )

    return RecentSessionsResponse(
        sessions=sessions,
        total=len(sessions),
    )


@router.post("/{session_id}/end", response_model=EndSessionResponse)
async def end_session(
    session_id: str,
    config: Config = Depends(get_config),
) -> EndSessionResponse:
    """End a conversation session.

    Clears the in-memory cache for the session. Database messages
    are preserved for history/analytics.

    Args:
        session_id: The session to end

    Returns:
        Confirmation with final message count
    """
    # Get message count before clearing
    message_count = len(_sessions.get(session_id, []))

    # Get or create conversation client to use its clear method
    db = db_service if db_service.pool is not None else None
    conv_client = get_conversation_client(config, db)
    conv_client.clear_session(session_id)

    logger.info(f"Ended session {session_id} with {message_count} messages")

    return EndSessionResponse(
        session_id=session_id,
        status="ended",
        message_count=message_count,
    )


@router.get("/{session_id}/status")
async def get_session_status(
    session_id: str,
) -> dict[str, Any]:
    """Get current status of a session.

    Returns information about whether a session exists and its state.

    Args:
        session_id: The session identifier

    Returns:
        Session status information
    """
    in_memory = session_id in _sessions and len(_sessions[session_id]) > 0
    in_db = False
    db_message_count = 0

    if db_service.pool is not None:
        try:
            history = await db_service.get_conversation_history(session_id, limit=1)
            if history:
                in_db = True
                # Get full count
                full_history = await db_service.get_conversation_history(session_id, limit=1000)
                db_message_count = len(full_history)
        except Exception:
            pass

    return {
        "session_id": session_id,
        "exists": in_memory or in_db,
        "in_memory": in_memory,
        "in_database": in_db,
        "memory_message_count": len(_sessions.get(session_id, [])),
        "database_message_count": db_message_count,
    }
