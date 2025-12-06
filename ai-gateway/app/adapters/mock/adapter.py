"""Mock backend adapter implementation.

Provides a fully-functional mock home automation backend for
testing and development without a real home automation system.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from app.core.interfaces.backend import EntityNotFoundError, HomeAutomationBackend
from app.core.models import (
    ActionResult,
    BackendCapabilities,
    DeviceAction,
    EntityInfo,
    EntityState,
)

from .state_store import StateStore

logger = logging.getLogger(__name__)


class MockBackend:
    """Mock home automation backend for testing.

    Simulates a home automation system with configurable behavior:
    - Latency simulation
    - Failure rate simulation
    - Pre-defined entities and states

    Configuration:
        latency_ms: Simulated network latency in milliseconds (default: 0)
        failure_rate: Probability of action failure (0.0-1.0, default: 0.0)
        entities: Optional custom entity list
        states: Optional custom initial states

    Example:
        >>> backend = MockBackend({
        ...     "latency_ms": 100,
        ...     "failure_rate": 0.1  # 10% failure rate
        ... })
        >>> await backend.connect()
        >>> state = await backend.get_entity_state("light.living_room")
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize mock backend.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.latency_ms = config.get("latency_ms", 0)
        self.failure_rate = config.get("failure_rate", 0.0)

        # Initialize state store
        entities = config.get("entities")
        states = config.get("states")
        self.state_store = StateStore(entities=entities, states=states)

        self._connected = False
        self._capabilities = BackendCapabilities(
            supports_scenes=True,
            supports_automations=False,
            supports_scripts=False,
            supports_areas=True,
            supports_device_registry=True,
            supports_history=False,
            supports_realtime_updates=False,
            supports_color_lights=True,
            supports_climate=True,
            supports_media_players=True,
            supports_notifications=False,
        )

        logger.info(
            f"MockBackend initialized: latency={self.latency_ms}ms, "
            f"failure_rate={self.failure_rate}"
        )

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "mock"

    @property
    def capabilities(self) -> BackendCapabilities:
        """Backend capabilities."""
        return self._capabilities

    async def connect(self) -> bool:
        """Establish connection (always succeeds for mock).

        Returns:
            True
        """
        await self._simulate_latency()
        self._connected = True
        logger.info("MockBackend connected")
        return True

    async def disconnect(self) -> None:
        """Disconnect from backend."""
        self._connected = False
        logger.info("MockBackend disconnected")

    async def health_check(self) -> bool:
        """Check if backend is healthy.

        Returns:
            True if connected
        """
        await self._simulate_latency()
        return self._connected

    async def get_entities(self, domain: str | None = None) -> list[EntityInfo]:
        """Get available entities.

        Args:
            domain: Optional domain filter

        Returns:
            List of EntityInfo
        """
        await self._simulate_latency()
        return self.state_store.get_entities(domain)

    async def get_entity_state(self, entity_id: str) -> EntityState | None:
        """Get entity state.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityState or None if not found
        """
        await self._simulate_latency()
        return self.state_store.get_state(entity_id)

    async def get_entity_states(
        self, entity_ids: list[str]
    ) -> dict[str, EntityState | None]:
        """Get states for multiple entities.

        Args:
            entity_ids: List of entity identifiers

        Returns:
            Dict mapping entity_id to state
        """
        await self._simulate_latency()
        return {eid: self.state_store.get_state(eid) for eid in entity_ids}

    async def execute_action(self, action: DeviceAction) -> ActionResult:
        """Execute a device action.

        Args:
            action: Action to execute

        Returns:
            ActionResult indicating success/failure
        """
        await self._simulate_latency()

        # Check for simulated failure
        if self._should_fail():
            logger.warning(f"Simulated failure for action: {action.entity_id}")
            return ActionResult.error_result(
                entity_id=action.entity_id,
                message="Simulated failure",
                error_code="simulated_failure",
            )

        # Check if entity exists
        if self.state_store.get_entity_info(action.entity_id) is None:
            return ActionResult.error_result(
                entity_id=action.entity_id,
                message=f"Entity not found: {action.entity_id}",
                error_code="entity_not_found",
            )

        # Apply action
        new_state = self.state_store.apply_action(action)
        if new_state is None:
            return ActionResult.error_result(
                entity_id=action.entity_id,
                message="Failed to apply action",
                error_code="action_failed",
            )

        logger.info(
            f"MockBackend executed: {action.action_type} on {action.entity_id} "
            f"-> state={new_state['state']}"
        )

        return ActionResult.success_result(
            entity_id=action.entity_id,
            message=f"Action {action.action_type} executed successfully",
            new_state=new_state,
        )

    async def execute_actions(
        self, actions: list[DeviceAction]
    ) -> list[ActionResult]:
        """Execute multiple actions.

        Args:
            actions: Actions to execute

        Returns:
            List of results
        """
        results = []
        for action in actions:
            result = await self.execute_action(action)
            results.append(result)
        return results

    async def get_all_states(self) -> list[EntityState]:
        """Get all entity states.

        Returns:
            List of EntityState for all entities
        """
        await self._simulate_latency()
        return [
            state
            for state in self.state_store.states.values()
            if state is not None
        ]

    def supports_domain(self, domain: str) -> bool:
        """Check if domain is supported.

        Args:
            domain: Domain to check

        Returns:
            True (mock supports all domains)
        """
        return True

    async def _simulate_latency(self) -> None:
        """Simulate network latency."""
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)

    def _should_fail(self) -> bool:
        """Check if this operation should fail.

        Returns:
            True if should fail based on failure_rate
        """
        if self.failure_rate <= 0:
            return False
        return random.random() < self.failure_rate

    def reset_states(self) -> None:
        """Reset all states to defaults."""
        self.state_store.reset()
        logger.info("MockBackend states reset to defaults")

    def set_entity_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> EntityState | None:
        """Manually set entity state (for testing).

        Args:
            entity_id: Entity identifier
            state: New state value
            attributes: Optional attributes to update

        Returns:
            Updated EntityState or None
        """
        return self.state_store.set_state(entity_id, state, attributes)
