"""Home automation backend protocol definition.

Defines the abstract interface that all backend adapters must implement.
This allows the AI Gateway to work with any home automation system
through a unified API.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from app.core.models.action import ActionResult, DeviceAction
from app.core.models.capability import BackendCapabilities
from app.core.models.entity import EntityInfo, EntityState


@runtime_checkable
class HomeAutomationBackend(Protocol):
    """Protocol for home automation backend adapters.

    All backend implementations must conform to this interface.
    Using Protocol allows for structural subtyping - any class
    that implements these methods is considered compatible.

    Lifecycle:
        1. Create instance with configuration
        2. Call connect() to establish connection
        3. Use get_entities(), get_entity_state(), execute_action()
        4. Call disconnect() when done

    Example Implementation:
        >>> class MyBackend:
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_backend"
        ...
        ...     @property
        ...     def capabilities(self) -> BackendCapabilities:
        ...         return BackendCapabilities()
        ...
        ...     async def connect(self) -> bool:
        ...         # Connect to backend
        ...         return True
        ...
        ...     async def disconnect(self) -> None:
        ...         # Cleanup
        ...         pass
        ...
        ...     async def health_check(self) -> bool:
        ...         return True
        ...
        ...     async def get_entities(self, domain: str | None = None) -> list[EntityInfo]:
        ...         return []
        ...
        ...     async def get_entity_state(self, entity_id: str) -> EntityState | None:
        ...         return None
        ...
        ...     async def execute_action(self, action: DeviceAction) -> ActionResult:
        ...         return ActionResult(success=True, entity_id=action.entity_id)
        ...
        ...     async def execute_actions(self, actions: list[DeviceAction]) -> list[ActionResult]:
        ...         return [await self.execute_action(a) for a in actions]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier.

        Returns:
            Unique name for this backend type (e.g., 'homeassistant', 'openhab')
        """
        ...

    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Backend capabilities.

        Returns:
            BackendCapabilities describing what this backend supports
        """
        ...

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the backend.

        Called once during initialization. Should validate credentials
        and establish any persistent connections.

        Returns:
            True if connection successful, False otherwise

        Raises:
            ConnectionError: If connection fails critically
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and cleanup resources.

        Called during shutdown. Should gracefully close any open
        connections and release resources.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is reachable and functioning.

        Returns:
            True if backend is healthy, False otherwise
        """
        ...

    @abstractmethod
    async def get_entities(self, domain: str | None = None) -> list[EntityInfo]:
        """Discover available entities.

        Args:
            domain: Optional domain filter (e.g., 'light', 'switch').
                   If None, returns all entities.

        Returns:
            List of EntityInfo for discovered entities
        """
        ...

    @abstractmethod
    async def get_entity_state(self, entity_id: str) -> EntityState | None:
        """Get current state of an entity.

        Args:
            entity_id: Entity identifier (e.g., 'light.living_room')

        Returns:
            EntityState if entity exists, None otherwise
        """
        ...

    async def get_entity_states(self, entity_ids: list[str]) -> dict[str, EntityState | None]:
        """Get states for multiple entities.

        Default implementation calls get_entity_state for each ID.
        Backends may override for batch optimization.

        Args:
            entity_ids: List of entity identifiers

        Returns:
            Dict mapping entity_id to EntityState (or None if not found)
        """
        results: dict[str, EntityState | None] = {}
        for entity_id in entity_ids:
            results[entity_id] = await self.get_entity_state(entity_id)
        return results

    @abstractmethod
    async def execute_action(self, action: DeviceAction) -> ActionResult:
        """Execute a single device action.

        Args:
            action: DeviceAction to execute

        Returns:
            ActionResult indicating success/failure
        """
        ...

    async def execute_actions(self, actions: list[DeviceAction]) -> list[ActionResult]:
        """Execute multiple actions sequentially.

        Default implementation calls execute_action for each action.
        Backends may override for batch/parallel optimization.

        Args:
            actions: List of DeviceActions to execute

        Returns:
            List of ActionResults in same order as input
        """
        results: list[ActionResult] = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
        return results

    async def get_all_states(self) -> list[EntityState]:
        """Get states for all entities.

        Convenience method to fetch all entity states at once.
        Default implementation discovers entities then fetches states.

        Returns:
            List of EntityState for all available entities
        """
        entities = await self.get_entities()
        states: list[EntityState] = []
        for entity in entities:
            state = await self.get_entity_state(entity.entity_id)
            if state is not None:
                states.append(state)
        return states

    def supports_domain(self, domain: str) -> bool:
        """Check if backend supports a specific domain.

        Args:
            domain: Domain to check (e.g., 'light', 'climate')

        Returns:
            True if domain is supported
        """
        domain_capability_map = {
            "light": "color_lights",
            "climate": "climate",
            "media_player": "media_players",
        }
        capability = domain_capability_map.get(domain)
        if capability:
            return self.capabilities.has_capability(capability)
        return True  # Assume basic domains are supported


class BackendError(Exception):
    """Base exception for backend errors."""

    def __init__(self, message: str, backend: str | None = None) -> None:
        """Initialize backend error.

        Args:
            message: Error description
            backend: Backend name (optional)
        """
        self.backend = backend
        super().__init__(f"[{backend}] {message}" if backend else message)


class BackendConnectionError(BackendError):
    """Raised when backend connection fails."""

    pass


class BackendAuthenticationError(BackendError):
    """Raised when backend authentication fails."""

    pass


class BackendUnavailableError(BackendError):
    """Raised when backend is temporarily unavailable."""

    pass


class EntityNotFoundError(BackendError):
    """Raised when an entity is not found."""

    def __init__(self, entity_id: str, backend: str | None = None) -> None:
        """Initialize entity not found error.

        Args:
            entity_id: Entity that was not found
            backend: Backend name (optional)
        """
        self.entity_id = entity_id
        super().__init__(f"Entity not found: {entity_id}", backend)


class ActionExecutionError(BackendError):
    """Raised when action execution fails."""

    def __init__(
        self,
        message: str,
        action: DeviceAction | None = None,
        backend: str | None = None,
    ) -> None:
        """Initialize action execution error.

        Args:
            message: Error description
            action: The action that failed (optional)
            backend: Backend name (optional)
        """
        self.action = action
        super().__init__(message, backend)
