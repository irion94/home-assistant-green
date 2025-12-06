"""API router for memory management endpoints.

This module implements endpoints for managing AI memory, knowledge base,
user preferences, cache, and training data.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.database import db_service
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


# ==========================================
# Request/Response Models
# ==========================================


class KnowledgeAddRequest(BaseModel):
    """Request to add knowledge entry."""

    content: str = Field(..., description="Knowledge content to store")
    source: str | None = Field(None, description="Source of the knowledge")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class KnowledgeAddResponse(BaseModel):
    """Response after adding knowledge."""

    id: int
    message: str


class KnowledgeSearchResult(BaseModel):
    """Single search result."""

    id: int
    content: str
    source: str | None
    tags: list[str]
    similarity: float
    created_at: str


class KnowledgeSearchResponse(BaseModel):
    """Response for knowledge search."""

    results: list[KnowledgeSearchResult]
    query: str


class PreferenceSetRequest(BaseModel):
    """Request to set a preference."""

    key: str = Field(..., description="Preference key")
    value: Any = Field(..., description="Preference value (any JSON-serializable)")
    category: str | None = Field(None, description="Category for grouping")


class PreferenceResponse(BaseModel):
    """Response for preference operations."""

    key: str
    value: Any
    message: str | None = None


class FeedbackRequest(BaseModel):
    """Request to record feedback."""

    training_id: int = Field(..., description="Training data entry ID")
    score: int = Field(..., ge=1, le=5, description="Feedback score (1-5)")


class TrainingExportResponse(BaseModel):
    """Response for training data export."""

    data: list[dict[str, Any]]
    count: int


class CacheStatsResponse(BaseModel):
    """Response for cache statistics."""

    total_entries: int
    total_hits: int
    active_entries: int


class TrainingStatsResponse(BaseModel):
    """Response for training data statistics."""

    total: int
    high_quality: int
    exported: int
    avg_score: float | None


class ConversationHistoryResponse(BaseModel):
    """Response for conversation history."""

    session_id: str
    messages: list[dict[str, Any]]


class RecentSessionsResponse(BaseModel):
    """Response for recent sessions list."""

    sessions: list[dict[str, Any]]


# ==========================================
# Knowledge Endpoints
# ==========================================


@router.post("/knowledge/add", response_model=KnowledgeAddResponse)
async def add_knowledge(request: KnowledgeAddRequest) -> KnowledgeAddResponse:
    """Add a new knowledge entry with automatic embedding generation."""
    try:
        # Generate embedding for the content
        embedding = await embedding_service.generate_embedding(request.content)

        # Store in database
        knowledge_id = await db_service.add_knowledge(
            content=request.content,
            embedding=embedding,
            source=request.source,
            tags=request.tags,
        )

        logger.info(f"Added knowledge entry {knowledge_id}")
        return KnowledgeAddResponse(
            id=knowledge_id,
            message="Knowledge entry added successfully",
        )

    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Maximum results"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity"),
) -> KnowledgeSearchResponse:
    """Search knowledge base using semantic similarity."""
    try:
        # Generate embedding for query
        query_embedding = await embedding_service.generate_embedding(query)

        # Search database
        results = await db_service.search_knowledge(
            query_embedding=query_embedding,
            limit=limit,
            min_similarity=min_similarity,
        )

        return KnowledgeSearchResponse(
            results=[KnowledgeSearchResult(**r) for r in results],
            query=query,
        )

    except Exception as e:
        logger.error(f"Error searching knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge/tags")
async def get_knowledge_by_tags(
    tags: str = Query(..., description="Comma-separated tags"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
) -> dict[str, Any]:
    """Get knowledge entries by tags."""
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        results = await db_service.get_knowledge_by_tags(tags=tag_list, limit=limit)
        return {"results": results, "tags": tag_list}

    except Exception as e:
        logger.error(f"Error getting knowledge by tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: int) -> dict[str, str]:
    """Delete a knowledge entry."""
    try:
        deleted = await db_service.delete_knowledge(knowledge_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        return {"message": f"Knowledge entry {knowledge_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Preference Endpoints
# ==========================================


@router.post("/preferences/set", response_model=PreferenceResponse)
async def set_preference(request: PreferenceSetRequest) -> PreferenceResponse:
    """Set a user preference."""
    try:
        await db_service.set_preference(
            key=request.key,
            value=request.value,
            category=request.category,
        )
        logger.info(f"Set preference: {request.key}")
        return PreferenceResponse(
            key=request.key,
            value=request.value,
            message="Preference set successfully",
        )

    except Exception as e:
        logger.error(f"Error setting preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences/get", response_model=PreferenceResponse)
async def get_preference(
    key: str = Query(..., description="Preference key"),
    default: Any = Query(None, description="Default value if not found"),
) -> PreferenceResponse:
    """Get a user preference."""
    try:
        value = await db_service.get_preference(key, default)
        return PreferenceResponse(key=key, value=value)

    except Exception as e:
        logger.error(f"Error getting preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences/category/{category}")
async def get_preferences_by_category(category: str) -> dict[str, Any]:
    """Get all preferences in a category."""
    try:
        preferences = await db_service.get_preferences_by_category(category)
        return {"category": category, "preferences": preferences}

    except Exception as e:
        logger.error(f"Error getting preferences by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/preferences/{key}")
async def delete_preference(key: str) -> dict[str, str]:
    """Delete a preference."""
    try:
        deleted = await db_service.delete_preference(key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Preference not found")
        return {"message": f"Preference '{key}' deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting preference: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Cache Endpoints
# ==========================================


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """Get cache statistics."""
    try:
        stats = await db_service.get_cache_stats()
        return CacheStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cache/clear")
async def clear_expired_cache() -> dict[str, Any]:
    """Clear expired cache entries."""
    try:
        count = await db_service.clear_expired_cache()
        return {"message": f"Cleared {count} expired cache entries", "count": count}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Training Data Endpoints
# ==========================================


@router.post("/training/feedback")
async def record_feedback(request: FeedbackRequest) -> dict[str, str]:
    """Record feedback for a training data entry."""
    try:
        updated = await db_service.update_feedback(
            training_id=request.training_id,
            score=request.score,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Training entry not found")
        return {"message": f"Feedback recorded for entry {request.training_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/export", response_model=TrainingExportResponse)
async def export_training_data(
    min_score: int = Query(3, ge=1, le=5, description="Minimum feedback score"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum entries to export"),
) -> TrainingExportResponse:
    """Export high-quality training data as JSONL format."""
    try:
        data = await db_service.export_training_data(
            min_score=min_score,
            limit=limit,
        )
        return TrainingExportResponse(data=data, count=len(data))

    except Exception as e:
        logger.error(f"Error exporting training data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training/stats", response_model=TrainingStatsResponse)
async def get_training_stats() -> TrainingStatsResponse:
    """Get training data statistics."""
    try:
        stats = await db_service.get_training_stats()
        return TrainingStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting training stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Conversation History Endpoints
# ==========================================


@router.get("/conversations/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum messages"),
) -> ConversationHistoryResponse:
    """Get conversation history for a session."""
    try:
        messages = await db_service.get_conversation_history(
            session_id=session_id,
            limit=limit,
        )
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=messages,
        )

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations", response_model=RecentSessionsResponse)
async def get_recent_sessions(
    limit: int = Query(10, ge=1, le=50, description="Maximum sessions"),
) -> RecentSessionsResponse:
    """Get recent conversation sessions."""
    try:
        sessions = await db_service.get_recent_sessions(limit=limit)
        return RecentSessionsResponse(sessions=sessions)

    except Exception as e:
        logger.error(f"Error getting recent sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Health/Status Endpoints
# ==========================================


@router.get("/status")
async def get_memory_status() -> dict[str, Any]:
    """Get memory service status."""
    try:
        db_connected = db_service.pool is not None
        embedding_available = await embedding_service.is_available()

        return {
            "database": "connected" if db_connected else "disconnected",
            "embedding_model": embedding_service.model,
            "embedding_available": embedding_available,
        }

    except Exception as e:
        logger.error(f"Error getting memory status: {e}")
        return {
            "database": "error",
            "embedding_model": embedding_service.model,
            "embedding_available": False,
            "error": str(e),
        }
