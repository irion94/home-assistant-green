"""Backend service for accessing the active home automation backend.

Provides a high-level interface for tools and routers to interact
with the configured home automation backend. This service abstracts
away the details of backend selection and loading.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.interfaces.backend import (
    BackendUnavailableError,
    HomeAutomationBackend,
)
from app.core.models import ActionResult, DeviceAction, EntityInfo, EntityState
from app.core.registry import BackendConfig, BackendRegistry

logger = logging.getLogger(__name__)


class BackendService:
    """Service for interacting with the active home automation backend.

    Provides a simplified interface for:
    - Executing device actions
    - Querying entity states
    - Discovering entities

    The service uses the globally active backend from BackendRegistry.
    If no backend is active, operations will raise BackendUnavailableError.

    Example:
        >>> # Get entity state
        >>> state = await BackendService.get_entity_state("light.living_room")
        >>> print(f"Light is {state.state}")

        >>> # Execute action
        >>> action = DeviceAction(
        ...     action_type="turn_on",
        ...     entity_id="light.living_room",
        ...     domain="light"
        ... )
        >>> result = await BackendService.execute_action(action)
        >>> print(f"Success: {result.success}")
    """

    @classmethod
    def get_backend(cls) -> HomeAutomationBackend:
        """Get the active backend instance.

        Returns:
            Active HomeAutomationBackend

        Raises:
            BackendUnavailableError: If no backend is active
        """
        return BackendRegistry.get_active()

    @classmethod
    def is_available(cls) -> bool:
        """Check if a backend is available.

        Returns:
            True if a backend is active
        """
        return BackendRegistry.is_active()

    @classmethod
    def get_backend_name(cls) -> str | None:
        """Get the name of the active backend.

        Returns:
            Backend name or None if no backend is active
        """
        return BackendRegistry.get_active_name()

    @classmethod
    async def health_check(cls) -> bool:
        """Check health of the active backend.

        Returns:
            True if backend is healthy, False otherwise
        """
        return await BackendRegistry.health_check()

    @classmethod
    async def execute_action(cls, action: DeviceAction) -> ActionResult:
        """Execute a device action on the active backend.

        Args:
            action: DeviceAction to execute

        Returns:
            ActionResult indicating success/failure

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        logger.debug(f"Executing action: {action.action_type} on {action.entity_id}")
        return await backend.execute_action(action)

    @classmethod
    async def execute_actions(cls, actions: list[DeviceAction]) -> list[ActionResult]:
        """Execute multiple actions sequentially.

        Args:
            actions: List of DeviceActions to execute

        Returns:
            List of ActionResults in same order as input

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        logger.debug(f"Executing {len(actions)} actions")
        return await backend.execute_actions(actions)

    @classmethod
    async def get_entity_state(cls, entity_id: str) -> EntityState | None:
        """Get current state of an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityState or None if not found

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        return await backend.get_entity_state(entity_id)

    @classmethod
    async def get_entity_states(
        cls, entity_ids: list[str]
    ) -> dict[str, EntityState | None]:
        """Get states for multiple entities.

        Args:
            entity_ids: List of entity identifiers

        Returns:
            Dict mapping entity_id to EntityState

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        return await backend.get_entity_states(entity_ids)

    @classmethod
    async def get_entities(cls, domain: str | None = None) -> list[EntityInfo]:
        """Discover available entities.

        Args:
            domain: Optional domain filter (e.g., 'light', 'switch')

        Returns:
            List of EntityInfo

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        return await backend.get_entities(domain)

    @classmethod
    async def get_all_states(cls) -> list[EntityState]:
        """Get states for all entities.

        Returns:
            List of EntityState for all entities

        Raises:
            BackendUnavailableError: If no backend is active
        """
        backend = cls.get_backend()
        return await backend.get_all_states()

    @classmethod
    def supports_domain(cls, domain: str) -> bool:
        """Check if the active backend supports a domain.

        Args:
            domain: Domain to check

        Returns:
            True if supported, False if not or no backend active
        """
        if not cls.is_available():
            return False
        return cls.get_backend().supports_domain(domain)


async def initialize_backend() -> None:
    """Initialize the backend from environment configuration.

    This function should be called during application startup.
    It loads the backend configuration from environment variables,
    loads the appropriate adapter, and activates the backend.

    Environment Variables:
        BACKEND_ADAPTER: Backend name (default: 'mock')
        BACKEND_SOURCE: Source type (default: 'builtin')
        BACKEND_PATH: Path for source='path'
        BACKEND_GIT_URL: Git URL for source='git'
        BACKEND_GIT_REF: Git ref for source='git'
        BACKEND_CONFIG: JSON string with backend configuration

    Raises:
        ValueError: If backend configuration is invalid
        ConnectionError: If backend connection fails
    """
    from app.core.registry import AdapterLoader

    # Load configuration from environment
    config = BackendConfig.from_env()
    logger.info(
        f"Initializing backend: adapter={config.adapter}, source={config.source}"
    )

    # Load the adapter (registers with BackendRegistry)
    await AdapterLoader.load_from_config(config)

    # Activate the backend
    await BackendRegistry.activate_from_config(config)

    logger.info(f"Backend '{config.adapter}' initialized successfully")


async def shutdown_backend() -> None:
    """Shutdown the active backend.

    Should be called during application shutdown to cleanly
    disconnect from the backend.
    """
    await BackendRegistry.shutdown()
    logger.info("Backend shutdown complete")
