"""Dynamic entity discovery service for Home Assistant.

This module fetches and caches entities from Home Assistant API,
enabling dynamic entity mapping without hardcoded configurations.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.ha_client import HAClient

logger = logging.getLogger(__name__)

# Domains that support common actions (turn on/off, control)
ACTIONABLE_DOMAINS = [
    "light",
    "switch",
    "climate",
    "media_player",
    "cover",
    "fan",
    "vacuum",
    "scene",
    "script",
    "input_boolean",
    "automation",
    "remote",
]


class EntityDiscovery:
    """Service for discovering and caching Home Assistant entities."""

    def __init__(self, ha_client: HAClient, cache_ttl: int = 300):
        """Initialize entity discovery service.

        Args:
            ha_client: Home Assistant API client
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.ha_client = ha_client
        self._cache: list[dict] = []
        self._cache_time: float | None = None
        self._cache_ttl = cache_ttl
        logger.info(f"EntityDiscovery initialized with cache_ttl={cache_ttl}s")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time:
            return False
        return (time.time() - self._cache_time) < self._cache_ttl

    async def get_entities(self, domain: str | None = None) -> list[dict]:
        """Get entities from Home Assistant with caching.

        Args:
            domain: Optional domain filter (e.g., 'light', 'switch')

        Returns:
            List of entity dictionaries with keys:
            - entity_id: Full entity ID (e.g., 'light.salon')
            - domain: Entity domain (e.g., 'light')
            - name: Friendly name from HA
            - state: Current state
        """
        if self._is_cache_valid():
            entities = self._cache
            logger.debug(f"Using cached entities ({len(entities)} total)")
        else:
            entities = await self._fetch_entities()
            self._cache = entities
            self._cache_time = time.time()
            logger.info(f"Refreshed entity cache: {len(entities)} actionable entities")

        if domain:
            filtered = [e for e in entities if e["domain"] == domain]
            logger.debug(f"Filtered to {len(filtered)} {domain} entities")
            return filtered
        return entities

    async def _fetch_entities(self) -> list[dict]:
        """Fetch all actionable entities from Home Assistant API."""
        try:
            states = await self.ha_client.get_states()
            if not states:
                logger.warning("No states returned from HA API")
                return []

            entities = []
            for state in states:
                entity_id = state.get("entity_id", "")
                domain = entity_id.split(".")[0] if "." in entity_id else ""

                if domain not in ACTIONABLE_DOMAINS:
                    continue

                friendly_name = state.get("attributes", {}).get("friendly_name", "")
                if not friendly_name:
                    # Use entity_id as fallback name
                    friendly_name = entity_id.replace("_", " ").replace(".", " ").title()

                entities.append({
                    "entity_id": entity_id,
                    "domain": domain,
                    "name": friendly_name,
                    "state": state.get("state", "unknown"),
                })

            # Sort by domain, then by name
            entities.sort(key=lambda e: (e["domain"], e["name"]))
            return entities

        except Exception as e:
            logger.error(f"Failed to fetch entities from HA: {e}")
            return []

    async def refresh_cache(self) -> list[dict]:
        """Force refresh the entity cache.

        Returns:
            Fresh list of entities
        """
        logger.info("Force refreshing entity cache")
        self._cache_time = None  # Invalidate cache
        return await self.get_entities()

    def get_entity_names(self, domain: str | None = None) -> list[str]:
        """Get list of entity friendly names (from cache).

        Args:
            domain: Optional domain filter

        Returns:
            List of friendly names
        """
        entities = self._cache if self._cache else []
        if domain:
            entities = [e for e in entities if e["domain"] == domain]
        return [e["name"] for e in entities]

    def find_entity_by_name(self, name: str) -> dict | None:
        """Find entity by friendly name (exact match from cache).

        Args:
            name: Friendly name to search

        Returns:
            Entity dict or None if not found
        """
        name_lower = name.lower()
        for entity in self._cache:
            if entity["name"].lower() == name_lower:
                return entity
        return None

    def build_entity_prompt(self, entities: list[dict] | None = None) -> str:
        """Build entity list formatted for LLM prompt.

        Args:
            entities: List of entities (uses cache if None)

        Returns:
            Formatted string for LLM prompt
        """
        if entities is None:
            entities = self._cache

        if not entities:
            return "No entities available."

        # Group by domain
        by_domain: dict[str, list[str]] = {}
        for e in entities:
            domain = e["domain"]
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(f'- "{e["name"]}" → {e["entity_id"]}')

        # Build prompt sections
        prompt_parts = []
        domain_order = ["light", "switch", "media_player", "climate", "cover", "fan", "scene", "script"]

        # Add domains in preferred order
        for domain in domain_order:
            if domain in by_domain:
                prompt_parts.append(f"{domain.upper()}S:")
                prompt_parts.extend(by_domain[domain])
                prompt_parts.append("")
                del by_domain[domain]

        # Add remaining domains
        for domain, items in sorted(by_domain.items()):
            prompt_parts.append(f"{domain.upper()}S:")
            prompt_parts.extend(items)
            prompt_parts.append("")

        return "\n".join(prompt_parts)


# Global instance
_entity_discovery: EntityDiscovery | None = None


def get_entity_discovery(ha_client: HAClient) -> EntityDiscovery:
    """Get or create global EntityDiscovery instance.

    Args:
        ha_client: Home Assistant client

    Returns:
        EntityDiscovery instance
    """
    global _entity_discovery
    if _entity_discovery is None:
        _entity_discovery = EntityDiscovery(ha_client)
    return _entity_discovery
