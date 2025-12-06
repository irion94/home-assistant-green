"""Backend-agnostic entity models.

Defines EntityInfo for entity metadata and EntityState for current
state information. These models provide a unified view of devices
across different home automation platforms.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EntityInfo(BaseModel):
    """Metadata about a home automation entity.

    Provides basic information about an entity without its current state.
    Used for entity discovery and listing available devices.

    Attributes:
        entity_id: Unique identifier for the entity
        domain: Entity domain (light, switch, sensor, etc.)
        name: Human-readable display name
        area: Room or area where entity is located
        supported_features: List of features the entity supports
        device_class: Device classification (e.g., temperature, humidity)
        metadata: Additional platform-specific information

    Examples:
        >>> EntityInfo(
        ...     entity_id="light.living_room",
        ...     domain="light",
        ...     name="Living Room Light",
        ...     area="Living Room",
        ...     supported_features=["brightness", "color", "color_temp"]
        ... )
    """

    entity_id: str = Field(..., description="Unique entity identifier")

    domain: str = Field(
        ...,
        description="Entity domain (light, switch, sensor, climate, etc.)",
    )

    name: str = Field(..., description="Human-readable display name")

    area: str | None = Field(
        default=None,
        description="Room or area where entity is located",
    )

    supported_features: list[str] = Field(
        default_factory=list,
        description="Features supported by this entity",
    )

    device_class: str | None = Field(
        default=None,
        description="Device classification (e.g., temperature, motion)",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional platform-specific metadata",
    )

    @property
    def is_light(self) -> bool:
        """Check if entity is a light."""
        return self.domain == "light"

    @property
    def is_switch(self) -> bool:
        """Check if entity is a switch."""
        return self.domain == "switch"

    @property
    def is_sensor(self) -> bool:
        """Check if entity is a sensor."""
        return self.domain == "sensor"

    @property
    def is_climate(self) -> bool:
        """Check if entity is a climate device."""
        return self.domain == "climate"

    @property
    def is_media_player(self) -> bool:
        """Check if entity is a media player."""
        return self.domain == "media_player"


class EntityState(BaseModel):
    """Current state of a home automation entity.

    Represents the current state and attributes of an entity.
    Used for querying device status and displaying information.

    Attributes:
        entity_id: Unique entity identifier
        state: Current state value (on, off, 21.5, playing, etc.)
        attributes: Entity-specific attributes (brightness, color, etc.)
        last_changed: When the state last changed
        last_updated: When the state was last updated
        available: Whether the entity is currently reachable
        domain: Entity domain (extracted from entity_id if not provided)

    Examples:
        >>> # Light entity state
        >>> EntityState(
        ...     entity_id="light.living_room",
        ...     state="on",
        ...     attributes={"brightness": 255, "color_mode": "brightness"}
        ... )

        >>> # Temperature sensor state
        >>> EntityState(
        ...     entity_id="sensor.outdoor_temperature",
        ...     state="21.5",
        ...     attributes={"unit_of_measurement": "°C", "device_class": "temperature"}
        ... )
    """

    entity_id: str = Field(..., description="Unique entity identifier")

    state: str = Field(..., description="Current state value")

    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Entity-specific attributes",
    )

    last_changed: datetime | None = Field(
        default=None,
        description="When the state last changed",
    )

    last_updated: datetime | None = Field(
        default=None,
        description="When the state was last updated (even if unchanged)",
    )

    available: bool = Field(
        default=True,
        description="Whether the entity is currently reachable",
    )

    domain: str | None = Field(
        default=None,
        description="Entity domain (auto-extracted from entity_id)",
    )

    def model_post_init(self, __context: Any) -> None:
        """Extract domain from entity_id if not provided."""
        if self.domain is None and "." in self.entity_id:
            object.__setattr__(self, "domain", self.entity_id.split(".", 1)[0])

    @property
    def is_on(self) -> bool:
        """Check if entity state is 'on' or equivalent."""
        return self.state.lower() in ("on", "true", "home", "open", "playing")

    @property
    def is_off(self) -> bool:
        """Check if entity state is 'off' or equivalent."""
        return self.state.lower() in ("off", "false", "away", "closed", "idle", "paused")

    @property
    def is_unavailable(self) -> bool:
        """Check if entity is unavailable."""
        return self.state.lower() in ("unavailable", "unknown") or not self.available

    @property
    def numeric_state(self) -> float | None:
        """Get state as a numeric value if possible.

        Returns:
            Float value of state, or None if not numeric
        """
        try:
            return float(self.state)
        except (ValueError, TypeError):
            return None

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Get an attribute value with optional default.

        Args:
            key: Attribute name
            default: Default value if attribute not found

        Returns:
            Attribute value or default
        """
        return self.attributes.get(key, default)

    @property
    def brightness_pct(self) -> int | None:
        """Get brightness as percentage (0-100).

        Returns:
            Brightness percentage or None if not applicable
        """
        brightness = self.attributes.get("brightness")
        if brightness is not None:
            return round(brightness / 255 * 100)
        return None

    @property
    def temperature(self) -> float | None:
        """Get temperature value.

        Returns:
            Temperature or None if not a temperature sensor/climate
        """
        # For climate devices
        if "current_temperature" in self.attributes:
            return self.attributes["current_temperature"]
        # For temperature sensors
        if self.attributes.get("device_class") == "temperature":
            return self.numeric_state
        return None

    @property
    def unit_of_measurement(self) -> str | None:
        """Get the unit of measurement for sensor entities."""
        return self.attributes.get("unit_of_measurement")
