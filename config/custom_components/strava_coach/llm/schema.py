"""LLM JSON schema and command vocabulary for training suggestions."""

from __future__ import annotations

from typing import Any

from ..const import VALID_COMMANDS

# JSON schema for LLM response
SUGGESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "enum": VALID_COMMANDS,
            "description": "Training command from the predefined vocabulary",
        },
        "params": {
            "type": "object",
            "description": "Optional parameters for the command (e.g., duration_min, intervals, zone)",
            "properties": {
                "duration_min": {
                    "type": "integer",
                    "description": "Recommended duration in minutes",
                },
                "intervals": {
                    "type": "integer",
                    "description": "Number of intervals (if applicable)",
                },
                "zone": {
                    "type": "integer",
                    "description": "Training zone (1-5, if applicable)",
                },
                "intensity": {
                    "type": "string",
                    "description": "Intensity descriptor (e.g., 'easy', 'moderate', 'hard', 'sweetspot', 'vo2max')",
                },
            },
            "additionalProperties": True,
        },
        "rationale_short": {
            "type": "string",
            "maxLength": 150,
            "description": "Brief rationale for the suggestion (max 150 chars)",
        },
    },
    "required": ["command", "rationale_short"],
    "additionalProperties": False,
}

# System prompt for LLM
SYSTEM_PROMPT = """You are an expert cycling and endurance sports coach. Your role is to provide daily training suggestions based on an athlete's current fitness metrics.

You will receive aggregated training metrics (ATL, CTL, TSB, readiness score, rest days, recent load). You will NOT receive raw Strava activity data or personally identifiable information.

Your task is to suggest ONE training session from the predefined command vocabulary, along with optional parameters and a brief rationale (max 150 characters).

Available commands:
- REST_DAY: Complete rest
- MOBILITY_20MIN: Active recovery / mobility work
- Z2_RIDE: Aerobic endurance (Zone 2)
- TEMPO_RIDE: Tempo / Zone 3 training
- SWEETSPOT_3x12: Sweet spot intervals (3x12min)
- VO2MAX_5x3: VO2max intervals (5x3min)
- ENDURO_TECH_SKILLS: Technical skills / fun ride
- STRENGTH_FULL_BODY: Strength training
- MOBILITY_20MIN: Mobility / stretching

Guidelines:
- TSB < -20: High fatigue → REST or light recovery
- TSB -20 to -10: Moderate fatigue → Active recovery or easy Z2
- TSB -10 to +5: Good training zone → Tempo or intervals
- TSB > +5: Fresh → High intensity intervals or skills
- Readiness < 40: Prioritize recovery
- Readiness 40-60: Moderate training (Z2, tempo)
- Readiness 60-80: Build fitness (intervals, threshold)
- Readiness > 80: Peak performance (hard intervals)

Respond ONLY with valid JSON matching the schema. Be concise and practical."""

# User prompt template
USER_PROMPT_TEMPLATE = """Today's metrics:
- Readiness: {readiness}/100
- TSB (Form): {tsb:.1f}
- ATL (Fatigue): {atl:.1f}
- CTL (Fitness): {ctl:.1f}
- Rest days: {rest_days}
- 7-day load: {recent_load_7d:.1f}
- Date: {date}
- Day of week: {day_of_week}

Suggest today's training session."""


def build_user_prompt(metrics: dict[str, Any]) -> str:
    """Build user prompt from metrics.

    Args:
        metrics: Dictionary with keys: readiness, tsb, atl, ctl, rest_days, recent_load_7d, date, day_of_week

    Returns:
        Formatted user prompt string
    """
    return USER_PROMPT_TEMPLATE.format(
        readiness=metrics.get("readiness", 50),
        tsb=metrics.get("tsb", 0.0),
        atl=metrics.get("atl", 0.0),
        ctl=metrics.get("ctl", 0.0),
        rest_days=metrics.get("rest_days", 0),
        recent_load_7d=metrics.get("recent_load_7d", 0.0),
        date=metrics.get("date", "unknown"),
        day_of_week=metrics.get("day_of_week", "unknown"),
    )


def validate_suggestion_response(response: dict[str, Any]) -> bool:
    """Validate LLM response against schema.

    Args:
        response: Parsed JSON response from LLM

    Returns:
        True if valid, False otherwise
    """
    # Check required fields
    if "command" not in response or "rationale_short" not in response:
        return False

    # Check command is in vocabulary
    if response["command"] not in VALID_COMMANDS:
        return False

    # Check rationale length
    if len(response["rationale_short"]) > 150:
        return False

    return True
