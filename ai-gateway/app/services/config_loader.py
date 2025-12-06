"""Configuration loader for entity mappings.

Loads entity configuration from YAML files, providing a centralized
way to customize entity mappings without modifying code.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default config paths (in order of precedence)
CONFIG_PATHS = [
    Path("/app/config/entities.yaml"),  # Docker container
    Path("config/entities.yaml"),  # Local development
    Path(__file__).parent.parent.parent / "config" / "entities.yaml",  # Relative to module
]


class EntityConfig:
    """Loaded entity configuration.

    Provides access to entity mappings, keywords, and other configuration
    loaded from YAML files.

    Attributes:
        entity_mapping: Friendly name -> entity ID mapping
        room_entities: Room name -> entity ID mapping
        room_names: Room key -> display name mapping
        sensor_entities: Sensor type -> list of entity IDs
        all_lights: List of all controllable light entity IDs
        keywords: Intent detection keywords by category
    """

    def __init__(self) -> None:
        """Initialize with empty configuration."""
        self.entity_mapping: dict[str, str] = {}
        self.room_entities: dict[str, str] = {}
        self.room_names: dict[str, str] = {}
        self.sensor_entities: dict[str, list[str]] = {}
        self.all_lights: list[str] = []
        self.keywords: dict[str, list[str]] = {
            "turn_on": [],
            "turn_off": [],
            "conversation_start": [],
            "conversation_end": [],
            "interrupt": [],
        }
        self._loaded = False

    def load(self, config_path: Path | None = None) -> None:
        """Load configuration from YAML file.

        Args:
            config_path: Optional explicit path to config file.
                        If not provided, searches default paths.

        Raises:
            FileNotFoundError: If no config file found
            yaml.YAMLError: If config file is invalid
        """
        if config_path is None:
            config_path = self._find_config_file()

        if config_path is None:
            logger.warning("No entity config file found, using defaults")
            self._load_defaults()
            return

        logger.info(f"Loading entity config from: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._parse_config(data)
        self._loaded = True
        logger.info(
            f"Loaded entity config: {len(self.entity_mapping)} mappings, "
            f"{len(self.room_entities)} rooms, {len(self.all_lights)} lights"
        )

    def _find_config_file(self) -> Path | None:
        """Find config file in default paths.

        Returns:
            Path to config file or None if not found
        """
        # Check environment variable first
        env_path = os.getenv("ENTITY_CONFIG_PATH")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Check default paths
        for path in CONFIG_PATHS:
            if path.exists():
                return path

        return None

    def _parse_config(self, data: dict[str, Any]) -> None:
        """Parse loaded YAML data into configuration.

        Args:
            data: Parsed YAML data
        """
        # Parse lights
        lights = data.get("lights", {})
        for room_key, light_config in lights.items():
            entity_id = light_config.get("entity_id")
            display_name = light_config.get("display_name", room_key)
            aliases = light_config.get("aliases", [])

            if entity_id:
                # Add to room entities
                self.room_entities[room_key] = entity_id
                self.room_names[room_key] = display_name

                # Add all aliases to entity mapping
                for alias in aliases:
                    self.entity_mapping[alias.lower()] = entity_id

        # Parse all_lights list
        self.all_lights = data.get("all_lights", [])

        # Parse all_lights aliases
        all_aliases = data.get("all_lights_aliases", [])
        for alias in all_aliases:
            self.entity_mapping[alias.lower()] = "all"

        # Add "all" to room entities
        self.room_entities["all"] = "all"
        self.room_names["all"] = "all lights"

        # Parse LED scripts
        led_scripts = data.get("led_scripts", {})
        for color, script_config in led_scripts.items():
            entity_id = script_config.get("entity_id")
            aliases = script_config.get("aliases", [])
            if entity_id:
                for alias in aliases:
                    self.entity_mapping[alias.lower()] = entity_id

        # Parse sensors
        self.sensor_entities = data.get("sensors", {})

        # Parse media players
        media_players = data.get("media_players", {})
        for player_key, player_config in media_players.items():
            entity_id = player_config.get("entity_id")
            aliases = player_config.get("aliases", [])
            if entity_id:
                for alias in aliases:
                    self.entity_mapping[alias.lower()] = entity_id

        # Parse keywords
        keywords = data.get("keywords", {})
        for keyword_type, keyword_list in keywords.items():
            if keyword_type in self.keywords:
                self.keywords[keyword_type] = [k.lower() for k in keyword_list]

    def _load_defaults(self) -> None:
        """Load default configuration (fallback when no file found)."""
        # Minimal defaults for basic operation
        self.room_entities = {
            "salon": "light.living_room",
            "all": "all",
        }
        self.room_names = {
            "salon": "living room",
            "all": "all lights",
        }
        self.entity_mapping = {
            "living room": "light.living_room",
            "salon": "light.living_room",
            "all": "all",
        }
        self.all_lights = ["light.living_room"]
        self.keywords = {
            "turn_on": ["turn on", "włącz", "zapal"],
            "turn_off": ["turn off", "wyłącz", "zgaś"],
            "conversation_start": ["let's talk", "porozmawiajmy"],
            "conversation_end": ["bye", "koniec"],
            "interrupt": ["stop"],
        }
        self._loaded = True


# Global singleton instance
_config: EntityConfig | None = None


def get_entity_config() -> EntityConfig:
    """Get the global entity configuration.

    Loads configuration on first access.

    Returns:
        EntityConfig singleton instance
    """
    global _config
    if _config is None:
        _config = EntityConfig()
        _config.load()
    return _config


def reload_entity_config(config_path: Path | None = None) -> EntityConfig:
    """Reload entity configuration.

    Forces a reload of the configuration from disk.

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Reloaded EntityConfig instance
    """
    global _config
    _config = EntityConfig()
    _config.load(config_path)
    return _config
