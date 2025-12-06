"""Backend capability model.

Defines what features a backend adapter supports, allowing the
AI Gateway to adapt its behavior based on backend capabilities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BackendCapabilities(BaseModel):
    """Capabilities supported by a home automation backend.

    Used to inform the AI Gateway about what features are available
    with the current backend. This allows graceful degradation when
    features aren't supported.

    Attributes:
        supports_scenes: Can create and execute scenes/groups
        supports_automations: Can manage automations
        supports_scripts: Can execute scripts
        supports_areas: Has area/room organization
        supports_device_registry: Has device/entity registry
        supports_history: Can query state history
        supports_realtime_updates: Supports WebSocket/push updates
        supports_color_lights: Can control RGB/color temperature lights
        supports_climate: Can control thermostats/HVAC
        supports_media_players: Can control media playback
        supports_notifications: Can send notifications
        max_concurrent_actions: Maximum parallel actions (0 = unlimited)
        custom_capabilities: Additional backend-specific capabilities

    Examples:
        >>> # Full-featured backend
        >>> BackendCapabilities(
        ...     supports_scenes=True,
        ...     supports_areas=True,
        ...     supports_realtime_updates=True
        ... )

        >>> # Basic backend
        >>> BackendCapabilities(
        ...     supports_scenes=False,
        ...     supports_areas=False,
        ...     max_concurrent_actions=1
        ... )
    """

    supports_scenes: bool = Field(
        default=True,
        description="Can create and execute scenes/groups",
    )

    supports_automations: bool = Field(
        default=False,
        description="Can manage automations",
    )

    supports_scripts: bool = Field(
        default=True,
        description="Can execute scripts",
    )

    supports_areas: bool = Field(
        default=True,
        description="Has area/room organization",
    )

    supports_device_registry: bool = Field(
        default=True,
        description="Has device/entity registry for discovery",
    )

    supports_history: bool = Field(
        default=False,
        description="Can query state history",
    )

    supports_realtime_updates: bool = Field(
        default=False,
        description="Supports WebSocket/push state updates",
    )

    supports_color_lights: bool = Field(
        default=True,
        description="Can control RGB and color temperature lights",
    )

    supports_climate: bool = Field(
        default=True,
        description="Can control thermostats and HVAC systems",
    )

    supports_media_players: bool = Field(
        default=True,
        description="Can control media playback devices",
    )

    supports_notifications: bool = Field(
        default=False,
        description="Can send notifications to devices",
    )

    max_concurrent_actions: int = Field(
        default=0,
        description="Maximum parallel actions (0 = unlimited)",
    )

    custom_capabilities: dict[str, bool] = Field(
        default_factory=dict,
        description="Additional backend-specific capabilities",
    )

    def has_capability(self, capability: str) -> bool:
        """Check if a specific capability is supported.

        Args:
            capability: Capability name (e.g., 'scenes', 'climate')

        Returns:
            True if capability is supported
        """
        # Check standard capabilities
        attr_name = f"supports_{capability}"
        if hasattr(self, attr_name):
            return getattr(self, attr_name)

        # Check custom capabilities
        return self.custom_capabilities.get(capability, False)

    @classmethod
    def full_capabilities(cls) -> BackendCapabilities:
        """Create a capabilities object with all features enabled.

        Useful for feature-complete backends like Home Assistant.

        Returns:
            BackendCapabilities with all standard features enabled
        """
        return cls(
            supports_scenes=True,
            supports_automations=True,
            supports_scripts=True,
            supports_areas=True,
            supports_device_registry=True,
            supports_history=True,
            supports_realtime_updates=True,
            supports_color_lights=True,
            supports_climate=True,
            supports_media_players=True,
            supports_notifications=True,
        )

    @classmethod
    def minimal_capabilities(cls) -> BackendCapabilities:
        """Create a capabilities object with minimal features.

        Useful for basic backends or mock implementations.

        Returns:
            BackendCapabilities with minimal features enabled
        """
        return cls(
            supports_scenes=False,
            supports_automations=False,
            supports_scripts=False,
            supports_areas=False,
            supports_device_registry=False,
            supports_history=False,
            supports_realtime_updates=False,
            supports_color_lights=True,  # Basic light control
            supports_climate=False,
            supports_media_players=False,
            supports_notifications=False,
            max_concurrent_actions=1,
        )
