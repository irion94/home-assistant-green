"""Core abstractions for the AI Gateway.

This package contains backend-agnostic interfaces, models, and registry
for home automation backends. These abstractions allow the AI Gateway
to work with any home automation system (Home Assistant, OpenHAB, etc.)
through a unified interface.

Modules:
    interfaces: Protocol definitions for backend implementations
    models: Backend-agnostic data models (DeviceAction, EntityState, etc.)
    registry: Backend registration and loading system
"""

from app.core.interfaces import HomeAutomationBackend
from app.core.models import (
    ActionResult,
    BackendCapabilities,
    DeviceAction,
    EntityInfo,
    EntityState,
)

__all__ = [
    "HomeAutomationBackend",
    "DeviceAction",
    "ActionResult",
    "EntityInfo",
    "EntityState",
    "BackendCapabilities",
]
