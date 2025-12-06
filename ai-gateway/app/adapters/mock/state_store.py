"""In-memory state storage for mock backend.

Manages entity states and applies actions to simulate device behavior.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.models import DeviceAction, EntityInfo, EntityState

from .fixtures import DEFAULT_ENTITIES, DEFAULT_STATES

logger = logging.getLogger(__name__)


class StateStore:
    """In-memory state storage for mock entities.

    Maintains entity information and states, and applies actions
    to simulate device behavior.

    Attributes:
        entities: Dict mapping entity_id to EntityInfo
        states: Dict mapping entity_id to EntityState
    """

    def __init__(
        self,
        entities: list[EntityInfo] | None = None,
        states: dict[str, EntityState] | None = None,
    ) -> None:
        """Initialize state store.

        Args:
            entities: Initial entity list (default: DEFAULT_ENTITIES)
            states: Initial state dict (default: DEFAULT_STATES)
        """
        self.entities: dict[str, EntityInfo] = {
            e.entity_id: e for e in (entities or DEFAULT_ENTITIES)
        }
        self.states: dict[str, EntityState] = copy.deepcopy(states or DEFAULT_STATES)

    def get_entities(self, domain: str | None = None) -> list[EntityInfo]:
        """Get all entities, optionally filtered by domain.

        Args:
            domain: Optional domain filter (e.g., 'light')

        Returns:
            List of EntityInfo matching the filter
        """
        if domain is None:
            return list(self.entities.values())
        return [e for e in self.entities.values() if e.domain == domain]

    def get_entity_info(self, entity_id: str) -> EntityInfo | None:
        """Get entity information.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityInfo or None if not found
        """
        return self.entities.get(entity_id)

    def get_state(self, entity_id: str) -> EntityState | None:
        """Get current state of an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityState or None if not found
        """
        return self.states.get(entity_id)

    def set_state(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
    ) -> EntityState | None:
        """Set entity state.

        Args:
            entity_id: Entity identifier
            state: New state value
            attributes: Optional attributes to update/merge

        Returns:
            Updated EntityState or None if entity not found
        """
        if entity_id not in self.states:
            logger.warning(f"Entity not found: {entity_id}")
            return None

        current = self.states[entity_id]
        new_attrs = dict(current.attributes)
        if attributes:
            new_attrs.update(attributes)

        now = datetime.now(timezone.utc)
        self.states[entity_id] = EntityState(
            entity_id=entity_id,
            state=state,
            attributes=new_attrs,
            last_changed=now if state != current.state else current.last_changed,
            last_updated=now,
            available=True,
            domain=current.domain,
        )

        return self.states[entity_id]

    def apply_action(self, action: DeviceAction) -> dict[str, Any] | None:
        """Apply a DeviceAction and return the new state.

        Simulates device behavior based on action type.

        Args:
            action: Action to apply

        Returns:
            New state dict or None if entity not found
        """
        entity_id = action.entity_id
        if entity_id not in self.states:
            logger.warning(f"Entity not found for action: {entity_id}")
            return None

        current = self.states[entity_id]
        domain = action.domain

        # Apply action based on type
        handler = self._get_action_handler(action.action_type)
        if handler:
            new_state, new_attrs = handler(current, action)
        else:
            # Default: just change state based on action type
            new_state, new_attrs = self._default_handler(current, action)

        # Update state
        updated = self.set_state(entity_id, new_state, new_attrs)
        if updated:
            return {
                "state": updated.state,
                "attributes": updated.attributes,
            }
        return None

    def _get_action_handler(self, action_type: str) -> Any | None:
        """Get handler function for action type."""
        handlers = {
            "turn_on": self._handle_turn_on,
            "turn_off": self._handle_turn_off,
            "toggle": self._handle_toggle,
            "set_brightness": self._handle_set_brightness,
            "set_color": self._handle_set_color,
            "set_color_temp": self._handle_set_color_temp,
            "set_temperature": self._handle_set_temperature,
            "set_hvac_mode": self._handle_set_hvac_mode,
            "play": self._handle_media_play,
            "pause": self._handle_media_pause,
            "stop": self._handle_media_stop,
            "volume_set": self._handle_volume_set,
            "mute": self._handle_mute,
        }
        return handlers.get(action_type)

    def _default_handler(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Default handler for unknown action types."""
        logger.info(f"Using default handler for {action.action_type}")
        return current.state, dict(current.attributes)

    def _handle_turn_on(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle turn_on action."""
        attrs = dict(current.attributes)

        if current.domain == "light":
            # Set brightness to 255 if not specified and currently 0
            if attrs.get("brightness", 0) == 0:
                attrs["brightness"] = 255
            attrs["color_mode"] = attrs.get("color_mode") or "brightness"

        return "on", attrs

    def _handle_turn_off(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle turn_off action."""
        attrs = dict(current.attributes)

        if current.domain == "light":
            attrs["brightness"] = 0
            attrs["color_mode"] = None

        return "off", attrs

    def _handle_toggle(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle toggle action."""
        if current.is_on:
            return self._handle_turn_off(current, action)
        return self._handle_turn_on(current, action)

    def _handle_set_brightness(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle set_brightness action."""
        attrs = dict(current.attributes)
        brightness = action.parameters.get("brightness", 100)

        # Convert percentage to 0-255 if needed
        if brightness <= 100:
            brightness = int(brightness * 255 / 100)

        attrs["brightness"] = brightness
        attrs["color_mode"] = "brightness"

        # Turn on if brightness > 0
        new_state = "on" if brightness > 0 else "off"
        return new_state, attrs

    def _handle_set_color(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle set_color action."""
        attrs = dict(current.attributes)

        if "rgb" in action.parameters:
            attrs["rgb_color"] = action.parameters["rgb"]
            attrs["color_mode"] = "rgb"
        elif "hs" in action.parameters:
            attrs["hs_color"] = action.parameters["hs"]
            attrs["color_mode"] = "hs"

        # Ensure light is on and has brightness
        if attrs.get("brightness", 0) == 0:
            attrs["brightness"] = 255

        return "on", attrs

    def _handle_set_color_temp(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle set_color_temp action."""
        attrs = dict(current.attributes)
        color_temp = action.parameters.get("color_temp", 370)

        attrs["color_temp"] = color_temp
        attrs["color_mode"] = "color_temp"

        # Ensure light is on
        if attrs.get("brightness", 0) == 0:
            attrs["brightness"] = 255

        return "on", attrs

    def _handle_set_temperature(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle set_temperature action for climate."""
        attrs = dict(current.attributes)
        temperature = action.parameters.get("temperature")

        if temperature is not None:
            attrs["temperature"] = temperature

        return current.state, attrs

    def _handle_set_hvac_mode(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle set_hvac_mode action for climate."""
        attrs = dict(current.attributes)
        hvac_mode = action.parameters.get("hvac_mode", "off")

        attrs["hvac_mode"] = hvac_mode
        return hvac_mode, attrs

    def _handle_media_play(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle media play action."""
        return "playing", dict(current.attributes)

    def _handle_media_pause(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle media pause action."""
        return "paused", dict(current.attributes)

    def _handle_media_stop(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle media stop action."""
        return "idle", dict(current.attributes)

    def _handle_volume_set(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle volume set action."""
        attrs = dict(current.attributes)
        level = action.parameters.get("volume_level", 0.5)
        attrs["volume_level"] = max(0.0, min(1.0, level))
        return current.state, attrs

    def _handle_mute(
        self,
        current: EntityState,
        action: DeviceAction,
    ) -> tuple[str, dict[str, Any]]:
        """Handle mute action."""
        attrs = dict(current.attributes)
        mute = action.parameters.get("mute", True)
        attrs["is_volume_muted"] = mute
        return current.state, attrs

    def add_entity(self, entity: EntityInfo, initial_state: EntityState) -> None:
        """Add a new entity to the store.

        Args:
            entity: Entity info
            initial_state: Initial state
        """
        self.entities[entity.entity_id] = entity
        self.states[entity.entity_id] = initial_state

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the store.

        Args:
            entity_id: Entity to remove

        Returns:
            True if removed, False if not found
        """
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.states.pop(entity_id, None)
            return True
        return False

    def reset(self) -> None:
        """Reset all states to defaults."""
        self.entities = {e.entity_id: e for e in DEFAULT_ENTITIES}
        self.states = copy.deepcopy(DEFAULT_STATES)
