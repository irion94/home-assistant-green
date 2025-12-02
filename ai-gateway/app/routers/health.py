"""Health check endpoints (Phase 8).

Provides liveness and readiness probes for Kubernetes-style health checks.
Tests connectivity to all critical dependencies.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.routers.dependencies import get_ha_client
from app.services.cache import CacheService, get_cache_service
from app.services.database import db_service
from app.services.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic liveness health check.

    Returns:
        Status message (always returns 200 OK if service is running)
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(
    cache: CacheService = Depends(get_cache_service),
    ha_client: HomeAssistantClient = Depends(get_ha_client),
) -> JSONResponse:
    """Deep readiness health check.

    Tests connectivity to all critical dependencies:
    - Redis cache
    - PostgreSQL database
    - Home Assistant API

    Returns:
        JSON response with status and individual check results
        HTTP 200 if all checks pass, HTTP 503 if any check fails
    """
    checks: dict[str, str] = {
        "api": "ok",
        "redis": await _check_redis(cache),
        "database": await _check_database(),
        "home_assistant": await _check_ha(ha_client),
    }

    all_ok = all(v == "ok" for v in checks.values())
    status_code = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
        },
    )


async def _check_redis(cache: CacheService) -> str:
    """Check Redis connectivity.

    Args:
        cache: CacheService instance

    Returns:
        "ok" if Redis is reachable, error message otherwise
    """
    if not cache.enabled:
        return "disabled"

    try:
        if cache.client is None:
            return "not_connected"

        # Test Redis with ping
        result = cache.client.ping()
        if result:
            return "ok"
        return "ping_failed"

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return f"error: {str(e)[:50]}"


async def _check_database() -> str:
    """Check PostgreSQL database connectivity.

    Returns:
        "ok" if database is reachable, error message otherwise
    """
    try:
        if not db_service.pool:
            return "disabled"

        # Test database with simple query
        async with db_service.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                return "ok"
            return "query_failed"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return f"error: {str(e)[:50]}"


async def _check_ha(ha_client: HomeAssistantClient) -> str:
    """Check Home Assistant API connectivity.

    Args:
        ha_client: HomeAssistantClient instance

    Returns:
        "ok" if HA is reachable and returns entities, error message otherwise
    """
    try:
        # Test HA API by fetching states
        states = await ha_client.get_states()

        if len(states) > 0:
            return "ok"
        return "no_entities"

    except Exception as e:
        logger.error(f"Home Assistant health check failed: {e}")
        return f"error: {str(e)[:50]}"
