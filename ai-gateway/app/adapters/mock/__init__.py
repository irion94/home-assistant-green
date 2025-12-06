"""Mock backend adapter for testing and development.

Provides a fully-functional mock home automation backend that
simulates devices without requiring a real home automation system.

Usage:
    >>> from app.core.registry import BackendRegistry
    >>> from app.adapters.mock import MockBackend
    >>>
    >>> # Register and activate
    >>> BackendRegistry.register("mock", MockBackend)
    >>> backend = await BackendRegistry.activate("mock", {"latency_ms": 100})
"""

from app.adapters.mock.adapter import MockBackend
from app.adapters.mock.fixtures import DEFAULT_ENTITIES, DEFAULT_STATES
from app.core.registry import BackendRegistry


def register() -> None:
    """Register the mock backend with the registry."""
    BackendRegistry.register("mock", MockBackend)


__all__ = [
    "MockBackend",
    "DEFAULT_ENTITIES",
    "DEFAULT_STATES",
    "register",
]
