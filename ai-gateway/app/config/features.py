"""Unified feature flag configuration (Phase 8).

Consolidates all feature flags from Phases 1-7 into a single validated config.
Enables centralized feature management with dependency validation.
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeatureFlags(BaseModel):
    """Application feature flags."""

    # Security (Phase 1)
    secrets_manager_enabled: bool = Field(
        default=True,
        description="Use Docker Secrets instead of environment variables",
    )

    # Architecture (Phase 3-4)
    panel_registry_enabled: bool = Field(
        default=True,
        description="Use PanelRegistry pattern for display panels",
    )

    unified_data_panel_enabled: bool = Field(
        default=True,
        description="Use consolidated DataDisplayPanel (Phase 4)",
    )

    # MQTT (Phase 5)
    mqtt_topic_version: str = Field(
        default="v1",
        description="MQTT topic version (v0=legacy, v1=current)",
    )

    # Performance (Phase 7)
    redis_cache_enabled: bool = Field(
        default=True,
        description="Enable Redis caching for hot paths",
    )

    retry_logic_enabled: bool = Field(
        default=True,
        description="Enable retry logic for external API calls",
    )

    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker pattern",
    )

    # Features
    learning_enabled: bool = Field(
        default=True,
        description="Enable learning systems (Context/Intent/Suggestion engines)",
    )

    streaming_stt_enabled: bool = Field(
        default=True,
        description="Enable streaming speech-to-text with interim results",
    )

    new_tools_enabled: bool = Field(
        default=True,
        description="Enable enhanced tools (WebView, MediaControl, LightControl)",
    )

    @classmethod
    def from_env(cls) -> FeatureFlags:
        """Load feature flags from environment variables.

        Returns:
            FeatureFlags instance with values from environment
        """
        return cls(
            secrets_manager_enabled=os.getenv("SECRETS_MANAGER_ENABLED", "true").lower() == "true",
            panel_registry_enabled=os.getenv("PANEL_REGISTRY_ENABLED", "true").lower() == "true",
            unified_data_panel_enabled=os.getenv("UNIFIED_DATA_PANEL_ENABLED", "true").lower() == "true",
            mqtt_topic_version=os.getenv("MQTT_TOPIC_VERSION", "v1"),
            redis_cache_enabled=os.getenv("REDIS_ENABLED", "true").lower() == "true",
            retry_logic_enabled=os.getenv("RETRY_LOGIC_ENABLED", "true").lower() == "true",
            circuit_breaker_enabled=os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true",
            learning_enabled=os.getenv("LEARNING_ENABLED", "true").lower() == "true",
            streaming_stt_enabled=os.getenv("STREAMING_STT_ENABLED", "true").lower() == "true",
            new_tools_enabled=os.getenv("NEW_TOOLS_ENABLED", "true").lower() == "true",
        )

    def validate_dependencies(self) -> list[str]:
        """Validate feature flag dependencies.

        Returns:
            List of validation warning messages (empty if all valid)
        """
        warnings = []

        # Learning requires database
        if self.learning_enabled:
            if os.getenv("DATABASE_ENABLED", "false").lower() != "true":
                warnings.append("LEARNING_ENABLED=true requires DATABASE_ENABLED=true")

        # Redis cache requires Redis service and library
        if self.redis_cache_enabled:
            try:
                import redis  # noqa: F401
            except ImportError:
                warnings.append("REDIS_ENABLED=true requires redis package (pip install redis)")

        # Retry logic requires tenacity library
        if self.retry_logic_enabled:
            try:
                import tenacity  # noqa: F401
            except ImportError:
                warnings.append("RETRY_LOGIC_ENABLED=true requires tenacity package")

        # MQTT version validation
        if self.mqtt_topic_version not in ["v0", "v1"]:
            warnings.append(f"MQTT_TOPIC_VERSION must be 'v0' or 'v1', got: {self.mqtt_topic_version}")

        return warnings

    def log_status(self) -> None:
        """Log current feature flag status."""
        logger.info("Feature Flags Status:")
        logger.info(f"  Security: secrets_manager={self.secrets_manager_enabled}")
        logger.info(f"  Architecture: panel_registry={self.panel_registry_enabled}, unified_data_panel={self.unified_data_panel_enabled}")
        logger.info(f"  MQTT: topic_version={self.mqtt_topic_version}")
        logger.info(f"  Performance: redis_cache={self.redis_cache_enabled}, retry_logic={self.retry_logic_enabled}, circuit_breaker={self.circuit_breaker_enabled}")
        logger.info(f"  Features: learning={self.learning_enabled}, streaming_stt={self.streaming_stt_enabled}, new_tools={self.new_tools_enabled}")


# Global instance
_feature_flags: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    """Get global feature flags instance.

    Returns:
        FeatureFlags singleton instance
    """
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags.from_env()

        # Validate and log warnings
        warnings = _feature_flags.validate_dependencies()
        for warning in warnings:
            logger.warning(f"Feature flag validation: {warning}")

        # Log status
        _feature_flags.log_status()

    return _feature_flags
