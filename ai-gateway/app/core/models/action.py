"""Backend-agnostic action models.

Defines DeviceAction for commanding devices and ActionResult for
responses. These models abstract away platform-specific details
like Home Assistant's domain.service format.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeviceAction(BaseModel):
    """Backend-agnostic device action command.

    Represents a single command to be executed on a home automation device.
    The backend adapter translates this into platform-specific calls.

    Attributes:
        action_type: The type of action to perform (turn_on, turn_off, etc.)
        entity_id: Target device/entity identifier
        domain: Device domain (light, switch, climate, media_player, etc.)
        parameters: Action-specific parameters (brightness, color, temperature)

    Examples:
        >>> # Turn on a light
        >>> DeviceAction(action_type="turn_on", entity_id="light.living_room", domain="light")

        >>> # Set brightness to 50%
        >>> DeviceAction(
        ...     action_type="set_brightness",
        ...     entity_id="light.bedroom",
        ...     domain="light",
        ...     parameters={"brightness": 50}
        ... )

        >>> # Set thermostat temperature
        >>> DeviceAction(
        ...     action_type="set_temperature",
        ...     entity_id="climate.thermostat",
        ...     domain="climate",
        ...     parameters={"temperature": 21.5, "hvac_mode": "heat"}
        ... )
    """

    action_type: Literal[
        "turn_on",
        "turn_off",
        "toggle",
        "set_brightness",
        "set_color",
        "set_color_temp",
        "set_temperature",
        "set_hvac_mode",
        "play",
        "pause",
        "stop",
        "next",
        "previous",
        "volume_set",
        "volume_up",
        "volume_down",
        "mute",
        "select_source",
        "custom",
    ] = Field(..., description="Type of action to perform")

    entity_id: str = Field(..., description="Target entity identifier")

    domain: str = Field(
        ...,
        description="Device domain (light, switch, climate, media_player, etc.)",
    )

    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "action_type": "turn_on",
                    "entity_id": "light.living_room",
                    "domain": "light",
                    "parameters": {},
                },
                {
                    "action_type": "set_brightness",
                    "entity_id": "light.bedroom",
                    "domain": "light",
                    "parameters": {"brightness": 75, "transition": 2},
                },
                {
                    "action_type": "set_temperature",
                    "entity_id": "climate.thermostat",
                    "domain": "climate",
                    "parameters": {"temperature": 22.0},
                },
            ]
        }


class ActionResult(BaseModel):
    """Result of executing a DeviceAction.

    Returned by backend adapters after attempting to execute an action.

    Attributes:
        success: Whether the action completed successfully
        entity_id: The entity that was targeted
        message: Human-readable status or error message
        new_state: Updated entity state after action (if available)
        error_code: Machine-readable error code (if failed)
        metadata: Additional backend-specific information

    Examples:
        >>> # Successful action
        >>> ActionResult(
        ...     success=True,
        ...     entity_id="light.living_room",
        ...     message="Light turned on",
        ...     new_state={"state": "on", "brightness": 255}
        ... )

        >>> # Failed action
        >>> ActionResult(
        ...     success=False,
        ...     entity_id="light.nonexistent",
        ...     message="Entity not found",
        ...     error_code="entity_not_found"
        ... )
    """

    success: bool = Field(..., description="Whether the action succeeded")

    entity_id: str = Field(..., description="Target entity identifier")

    message: str | None = Field(
        default=None,
        description="Human-readable status or error message",
    )

    new_state: dict[str, Any] | None = Field(
        default=None,
        description="Updated entity state after action",
    )

    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code if failed",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional backend-specific information",
    )

    @classmethod
    def success_result(
        cls,
        entity_id: str,
        message: str | None = None,
        new_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ActionResult:
        """Create a successful action result.

        Args:
            entity_id: Target entity identifier
            message: Optional success message
            new_state: Optional new entity state
            **kwargs: Additional metadata

        Returns:
            ActionResult with success=True
        """
        return cls(
            success=True,
            entity_id=entity_id,
            message=message,
            new_state=new_state,
            metadata=kwargs,
        )

    @classmethod
    def error_result(
        cls,
        entity_id: str,
        message: str,
        error_code: str | None = None,
        **kwargs: Any,
    ) -> ActionResult:
        """Create a failed action result.

        Args:
            entity_id: Target entity identifier
            message: Error message
            error_code: Optional machine-readable error code
            **kwargs: Additional metadata

        Returns:
            ActionResult with success=False
        """
        return cls(
            success=False,
            entity_id=entity_id,
            message=message,
            error_code=error_code,
            metadata=kwargs,
        )
