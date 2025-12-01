"""Shared text utilities for AI Gateway.

This module contains text processing functions used across multiple services.
"""

from __future__ import annotations


def detect_language(text: str) -> str:
    """Detect language from text based on Polish characters.

    Args:
        text: Text to analyze

    Returns:
        Language code ('pl' or 'en')
    """
    polish_chars = set('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ')
    return "pl" if any(char in polish_chars for char in text) else "en"


def build_entity_prompt(entities: list[dict]) -> str:
    """Build entity list formatted for LLM prompt.

    Args:
        entities: List of entity dicts with 'domain', 'name', 'entity_id'

    Returns:
        Formatted string for prompt
    """
    if not entities:
        return "No entities available."

    # Group by domain
    by_domain: dict[str, list[str]] = {}
    for e in entities:
        domain = e.get("domain", "unknown")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(f'- "{e.get("name", "")}" → {e.get("entity_id", "")}')

    # Build sections
    lines = []
    domain_order = ["light", "switch", "media_player", "climate", "cover", "fan"]

    for domain in domain_order:
        if domain in by_domain:
            lines.append(f"{domain.upper()}S:")
            lines.extend(by_domain[domain])
            lines.append("")
            del by_domain[domain]

    # Remaining domains
    for domain, items in sorted(by_domain.items()):
        lines.append(f"{domain.upper()}S:")
        lines.extend(items)
        lines.append("")

    return "\n".join(lines)
