"""Rule-based training suggestion generator (no LLM)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from ..const import (
    COMMAND_ENDURO_TECH_SKILLS,
    COMMAND_MOBILITY_20MIN,
    COMMAND_REST_DAY,
    COMMAND_STRENGTH_FULL_BODY,
    COMMAND_SWEETSPOT_3X12,
    COMMAND_TEMPO_RIDE,
    COMMAND_VO2MAX_5X3,
    COMMAND_Z2_RIDE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingSuggestion:
    """Training suggestion with command and rationale."""

    command: str
    params: dict[str, str | int | float]
    rationale_short: str


def generate_suggestion(
    readiness: float,
    tsb: float,
    atl: float,
    ctl: float,
    rest_days: int,
    recent_load_7d: float,
    day_of_week: int | None = None,
) -> TrainingSuggestion:
    """Generate a rule-based training suggestion.

    Args:
        readiness: Current readiness score (0-100)
        tsb: Training Stress Balance (form)
        atl: Acute Training Load (fatigue)
        ctl: Chronic Training Load (fitness)
        rest_days: Consecutive rest days
        recent_load_7d: Total training load in last 7 days
        day_of_week: Day of week (0=Monday, 6=Sunday), optional

    Returns:
        TrainingSuggestion with command, params, and rationale
    """
    _LOGGER.debug(
        "Generating suggestion: readiness=%.1f, tsb=%.1f, atl=%.1f, ctl=%.1f, rest_days=%d",
        readiness,
        tsb,
        atl,
        ctl,
        rest_days,
    )

    # Rule 1: Very low readiness or high fatigue -> REST
    if readiness < 30 or tsb < -20:
        return TrainingSuggestion(
            command=COMMAND_REST_DAY,
            params={},
            rationale_short="High fatigue detected. Prioritize recovery today.",
        )

    # Rule 2: Moderate fatigue or 0 rest days after heavy week -> ACTIVE RECOVERY
    if (30 <= readiness < 50 or tsb < -10) and rest_days == 0:
        return TrainingSuggestion(
            command=COMMAND_MOBILITY_20MIN,
            params={"duration_min": 20},
            rationale_short="Moderate fatigue. Active recovery recommended.",
        )

    # Rule 3: Too much rest (3+ days) and decent readiness -> EASE BACK
    if rest_days >= 3 and readiness >= 50:
        return TrainingSuggestion(
            command=COMMAND_Z2_RIDE,
            params={"duration_min": 45, "zone": 2},
            rationale_short="Extended rest period. Ease back with aerobic training.",
        )

    # Rule 4: Good readiness (60-75) and moderate form -> TEMPO/SWEETSPOT
    if 60 <= readiness < 75 and -5 <= tsb <= 5:
        return TrainingSuggestion(
            command=COMMAND_SWEETSPOT_3X12,
            params={"intervals": 3, "duration_min": 12, "intensity": "sweetspot"},
            rationale_short="Good readiness. Build fitness with threshold intervals.",
        )

    # Rule 5: High readiness (75+) and fresh (TSB > 5) -> HIGH INTENSITY
    if readiness >= 75 and tsb > 5:
        return TrainingSuggestion(
            command=COMMAND_VO2MAX_5X3,
            params={"intervals": 5, "duration_min": 3, "intensity": "vo2max"},
            rationale_short="Excellent readiness. High-intensity intervals recommended.",
        )

    # Rule 6: Decent readiness but high ATL/CTL ratio -> ACTIVE RECOVERY or STRENGTH
    if 50 <= readiness < 70 and ctl > 0 and (atl / ctl) > 1.3:
        if day_of_week in (5, 6):  # Weekend
            return TrainingSuggestion(
                command=COMMAND_ENDURO_TECH_SKILLS,
                params={"duration_min": 90},
                rationale_short="High training load. Focus on skills instead of volume.",
            )
        else:
            return TrainingSuggestion(
                command=COMMAND_STRENGTH_FULL_BODY,
                params={"duration_min": 45},
                rationale_short="High training load. Cross-train with strength work.",
            )

    # Rule 7: Moderate readiness and balanced form -> TEMPO
    if 50 <= readiness < 70 and -5 <= tsb <= 10:
        return TrainingSuggestion(
            command=COMMAND_TEMPO_RIDE,
            params={"duration_min": 60, "zone": 3},
            rationale_short="Balanced training state. Tempo session to maintain fitness.",
        )

    # Rule 8: Low but not critical readiness -> Z2 AEROBIC
    if 40 <= readiness < 60:
        return TrainingSuggestion(
            command=COMMAND_Z2_RIDE,
            params={"duration_min": 60, "zone": 2},
            rationale_short="Moderate readiness. Build aerobic base with Z2 training.",
        )

    # Default fallback: EASY AEROBIC
    return TrainingSuggestion(
        command=COMMAND_Z2_RIDE,
        params={"duration_min": 45, "zone": 2},
        rationale_short="Steady aerobic training to maintain fitness.",
    )


def suggest_for_date(
    date: datetime,
    metrics: dict[str, float | int],
) -> TrainingSuggestion:
    """Generate suggestion for a specific date.

    Args:
        date: Target date
        metrics: Dictionary with keys: readiness, tsb, atl, ctl, rest_days, recent_load_7d

    Returns:
        TrainingSuggestion
    """
    day_of_week = date.weekday()  # 0=Monday, 6=Sunday

    return generate_suggestion(
        readiness=metrics.get("readiness", 50.0),
        tsb=metrics.get("tsb", 0.0),
        atl=metrics.get("atl", 0.0),
        ctl=metrics.get("ctl", 0.0),
        rest_days=metrics.get("rest_days", 0),
        recent_load_7d=metrics.get("recent_load_7d", 0.0),
        day_of_week=day_of_week,
    )
