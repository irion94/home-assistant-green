"""Client Configuration Router.

Serves client-specific configuration for React Dashboard.
Configuration is stored per-client in JSON files or environment variables.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


class EntityConfig(BaseModel):
    """Entity configuration model."""

    name: str
    entity_id: str
    icon: str | None = None


class SensorConfig(BaseModel):
    """Sensor configuration model."""

    name: str
    entity_id: str
    unit: str | None = None
    icon: str | None = None


class ThemeConfig(BaseModel):
    """Theme configuration model."""

    primaryColor: str = "#03a9f4"
    secondaryColor: str = "#ff9800"
    accentColor: str = "#4caf50"
    backgroundColor: str = "#0a0a0a"
    surfaceColor: str = "#1a1a1a"
    textColor: str = "#ffffff"
    textSecondaryColor: str = "#a0a0a0"
    clientName: str = "Smart Home"
    logoUrl: str | None = None
    faviconUrl: str | None = None
    borderRadius: str = "medium"
    darkMode: bool = True


class FeatureFlags(BaseModel):
    """Feature flags model."""

    voiceControl: bool = True
    climatePanel: bool = False
    cameraPanel: bool = False
    mediaPanel: bool = True
    debugPanel: bool = False


class ClientConfigResponse(BaseModel):
    """Client configuration response model."""

    clientId: str
    clientName: str
    lights: dict[str, EntityConfig]
    sensors: dict[str, SensorConfig]
    climate: dict[str, EntityConfig]
    media: dict[str, EntityConfig]
    theme: ThemeConfig
    features: FeatureFlags


# Default configuration (used when no client-specific config exists)
DEFAULT_CONFIG: dict[str, Any] = {
    "clientId": "default",
    "clientName": "Smart Home Dashboard",
    "lights": {},
    "sensors": {},
    "climate": {},
    "media": {},
    "theme": ThemeConfig().model_dump(),
    "features": FeatureFlags().model_dump(),
}


def get_config_path() -> Path:
    """Get the path to client configuration directory.

    Returns:
        Path to config directory
    """
    # Check environment variable first
    config_dir = os.getenv("CLIENT_CONFIG_DIR", "/data/clients")
    return Path(config_dir)


def load_client_config(client_id: str) -> dict[str, Any]:
    """Load client configuration from JSON file.

    Args:
        client_id: Client identifier

    Returns:
        Client configuration dictionary
    """
    config_path = get_config_path() / f"{client_id}.json"

    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                logger.info(f"Loaded config for client: {client_id}")
                return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_path}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Invalid configuration file for client: {client_id}",
            ) from e
        except Exception as e:
            logger.error(f"Error reading config file {config_path}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error loading configuration for client: {client_id}",
            ) from e

    # Return default config if no client-specific file exists
    logger.info(f"No config file found for client: {client_id}, using defaults")
    return {**DEFAULT_CONFIG, "clientId": client_id}


@router.get("/{client_id}", response_model=ClientConfigResponse)
async def get_client_config(client_id: str) -> ClientConfigResponse:
    """Get configuration for a specific client.

    Args:
        client_id: Client identifier (e.g., "wojcik_igor")

    Returns:
        Client configuration including entities, theme, and features
    """
    config = load_client_config(client_id)
    return ClientConfigResponse(**config)


@router.get("/", response_model=ClientConfigResponse)
async def get_default_config() -> ClientConfigResponse:
    """Get default configuration.

    Returns:
        Default client configuration
    """
    return ClientConfigResponse(**DEFAULT_CONFIG)


@router.get("/{client_id}/theme", response_model=ThemeConfig)
async def get_client_theme(client_id: str) -> ThemeConfig:
    """Get theme configuration for a specific client.

    Args:
        client_id: Client identifier

    Returns:
        Theme configuration
    """
    config = load_client_config(client_id)
    theme_data = config.get("theme", DEFAULT_CONFIG["theme"])
    return ThemeConfig(**theme_data)


@router.get("/{client_id}/features", response_model=FeatureFlags)
async def get_client_features(client_id: str) -> FeatureFlags:
    """Get feature flags for a specific client.

    Args:
        client_id: Client identifier

    Returns:
        Feature flags
    """
    config = load_client_config(client_id)
    features_data = config.get("features", DEFAULT_CONFIG["features"])
    return FeatureFlags(**features_data)
