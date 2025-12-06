"""Backend-agnostic models for home automation.

This module defines data models that are independent of any specific
home automation platform. These models serve as the common language
between the AI Gateway and backend adapters.
"""

from app.core.models.action import ActionResult, DeviceAction
from app.core.models.capability import BackendCapabilities
from app.core.models.entity import EntityInfo, EntityState

__all__ = [
    "DeviceAction",
    "ActionResult",
    "EntityInfo",
    "EntityState",
    "BackendCapabilities",
]
