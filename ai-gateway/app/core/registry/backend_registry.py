"""Central registry for home automation backends.

Provides registration, instantiation, and lifecycle management
for backend adapters. Only one backend can be active at a time
(per the architecture decision of single-backend per instance).
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from app.core.interfaces.backend import (
    BackendConnectionError,
    BackendUnavailableError,
    HomeAutomationBackend,
)
from app.core.registry.config import BackendConfig

logger = logging.getLogger(__name__)

# Type variable for backend classes
T = TypeVar("T", bound=HomeAutomationBackend)


class BackendRegistry:
    """Central registry for home automation backend adapters.

    Manages registration of backend adapter classes and activation
    of backend instances. Only one backend can be active at a time.

    Class Attributes:
        _backends: Mapping of backend names to adapter classes
        _active_instance: Currently active backend instance
        _active_name: Name of the active backend

    Example:
        >>> # Register a backend class
        >>> BackendRegistry.register("mock", MockBackend)

        >>> # Activate with configuration
        >>> backend = await BackendRegistry.activate("mock", {"latency_ms": 100})

        >>> # Get the active backend
        >>> backend = BackendRegistry.get_active()

        >>> # Shutdown
        >>> await BackendRegistry.shutdown()
    """

    _backends: dict[str, type[HomeAutomationBackend]] = {}
    _active_instance: HomeAutomationBackend | None = None
    _active_name: str | None = None
    _active_config: BackendConfig | None = None

    @classmethod
    def register(cls, name: str, backend_class: type[HomeAutomationBackend]) -> None:
        """Register a backend adapter class.

        Args:
            name: Unique identifier for this backend
            backend_class: Backend adapter class (must implement HomeAutomationBackend)

        Raises:
            ValueError: If name is already registered
            TypeError: If backend_class doesn't implement HomeAutomationBackend
        """
        if name in cls._backends:
            logger.warning(f"Backend '{name}' already registered, overwriting")

        # Verify the class implements the protocol
        if not isinstance(backend_class, type):
            raise TypeError(f"backend_class must be a class, got {type(backend_class)}")

        cls._backends[name] = backend_class
        logger.info(f"Registered backend adapter: {name}")

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a backend adapter.

        Args:
            name: Backend name to unregister

        Returns:
            True if backend was unregistered, False if not found
        """
        if name in cls._backends:
            del cls._backends[name]
            logger.info(f"Unregistered backend adapter: {name}")
            return True
        return False

    @classmethod
    def list_backends(cls) -> list[str]:
        """List all registered backend names.

        Returns:
            List of registered backend names
        """
        return list(cls._backends.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a backend is registered.

        Args:
            name: Backend name to check

        Returns:
            True if backend is registered
        """
        return name in cls._backends

    @classmethod
    async def activate(
        cls,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> HomeAutomationBackend:
        """Activate a backend by name.

        Creates an instance of the registered backend class and
        establishes a connection. Only one backend can be active.

        Args:
            name: Registered backend name
            config: Backend-specific configuration

        Returns:
            Activated backend instance

        Raises:
            ValueError: If backend name is not registered
            BackendConnectionError: If connection fails
        """
        if name not in cls._backends:
            available = ", ".join(cls._backends.keys()) or "none"
            raise ValueError(
                f"Unknown backend: '{name}'. Available backends: {available}"
            )

        # Shutdown existing backend if any
        if cls._active_instance is not None:
            logger.info(f"Deactivating current backend: {cls._active_name}")
            await cls.shutdown()

        backend_class = cls._backends[name]
        config = config or {}

        logger.info(f"Activating backend: {name}")
        try:
            # Create instance
            instance = backend_class(config)

            # Connect
            connected = await instance.connect()
            if not connected:
                raise BackendConnectionError(
                    f"Backend '{name}' connect() returned False",
                    backend=name,
                )

            cls._active_instance = instance
            cls._active_name = name
            logger.info(f"Backend '{name}' activated successfully")

            return instance

        except BackendConnectionError:
            raise
        except Exception as e:
            logger.error(f"Failed to activate backend '{name}': {e}")
            raise BackendConnectionError(
                f"Failed to activate backend: {e}",
                backend=name,
            ) from e

    @classmethod
    async def activate_from_config(cls, backend_config: BackendConfig) -> HomeAutomationBackend:
        """Activate a backend from a BackendConfig.

        This is the main entry point for loading backends from
        environment configuration.

        Args:
            backend_config: Configuration specifying which backend to load

        Returns:
            Activated backend instance

        Raises:
            ValueError: If backend is not registered
            BackendConnectionError: If connection fails
        """
        cls._active_config = backend_config
        return await cls.activate(backend_config.adapter, backend_config.config)

    @classmethod
    def get_active(cls) -> HomeAutomationBackend:
        """Get the currently active backend instance.

        Returns:
            Active backend instance

        Raises:
            RuntimeError: If no backend is active
        """
        if cls._active_instance is None:
            raise BackendUnavailableError(
                "No backend is active. Call activate() first."
            )
        return cls._active_instance

    @classmethod
    def get_active_name(cls) -> str | None:
        """Get the name of the active backend.

        Returns:
            Name of active backend, or None if no backend is active
        """
        return cls._active_name

    @classmethod
    def get_active_config(cls) -> BackendConfig | None:
        """Get the configuration of the active backend.

        Returns:
            BackendConfig of active backend, or None
        """
        return cls._active_config

    @classmethod
    def is_active(cls) -> bool:
        """Check if a backend is currently active.

        Returns:
            True if a backend is active
        """
        return cls._active_instance is not None

    @classmethod
    async def shutdown(cls) -> None:
        """Shutdown the active backend.

        Disconnects and releases the active backend instance.
        Safe to call even if no backend is active.
        """
        if cls._active_instance is not None:
            name = cls._active_name
            try:
                await cls._active_instance.disconnect()
                logger.info(f"Backend '{name}' disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting backend '{name}': {e}")
            finally:
                cls._active_instance = None
                cls._active_name = None

    @classmethod
    async def health_check(cls) -> bool:
        """Check health of the active backend.

        Returns:
            True if backend is healthy, False if unhealthy or inactive
        """
        if cls._active_instance is None:
            return False
        try:
            return await cls._active_instance.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @classmethod
    def reset(cls) -> None:
        """Reset the registry (for testing).

        Clears all registered backends and active instance.
        Does NOT call disconnect - use shutdown() first.
        """
        cls._backends.clear()
        cls._active_instance = None
        cls._active_name = None
        cls._active_config = None
        logger.debug("Backend registry reset")
