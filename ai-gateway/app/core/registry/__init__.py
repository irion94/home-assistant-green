"""Backend registry and loading system.

This module provides the infrastructure for registering, loading,
and managing home automation backend adapters. Supports multiple
sources including built-in adapters, Python packages, local paths,
and git repositories.
"""

from app.core.registry.backend_registry import BackendRegistry
from app.core.registry.config import BackendConfig
from app.core.registry.loader import AdapterLoader

__all__ = [
    "BackendRegistry",
    "BackendConfig",
    "AdapterLoader",
]
