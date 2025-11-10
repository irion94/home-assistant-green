"""Readiness score calculation (0-100 scale)."""

from __future__ import annotations

import logging
import math

_LOGGER = logging.getLogger(__name__)


def calculate_readiness(
    tsb: float,
    monotony: float,
    rest_days: int,
    atl: float | None = None,
    ctl: float | None = None,
) -> float:
    """Calculate overall readiness score (0-100).

    Readiness combines:
    - TSB (form/freshness)
    - Training monotony (variety)
    - Recent rest days
    - Optional: ATL/CTL ratios

    Args:
        tsb: Training Stress Balance (form)
        monotony: Training monotony index (higher = more monotonous)
        rest_days: Number of consecutive rest days (0 if trained today)
        atl: Acute Training Load (optional, for additional context)
        ctl: Chronic Training Load (optional, for additional context)

    Returns:
        Readiness score from 0 (not ready) to 100 (very ready)
    """
    # Component 1: TSB-based freshness (40% weight)
    # TSB typically ranges from -30 (fatigued) to +25 (very fresh)
    # Optimal TSB for training is around 0 to +5
    tsb_score = _calculate_tsb_component(tsb)

    # Component 2: Monotony penalty (20% weight)
    # Lower monotony (more variety) is better
    monotony_score = _calculate_monotony_component(monotony)

    # Component 3: Rest days factor (20% weight)
    # 1-2 rest days is good, 0 or 3+ is suboptimal
    rest_score = _calculate_rest_component(rest_days)

    # Component 4: Load ratio (20% weight)
    # ATL/CTL ratio indicates training ramp rate
    load_score = 50.0  # Default neutral
    if atl is not None and ctl is not None and ctl > 0:
        load_score = _calculate_load_ratio_component(atl, ctl)

    # Weighted combination (heavier penalty on TSB)
    readiness = (
        0.50 * tsb_score + 0.15 * monotony_score + 0.15 * rest_score + 0.20 * load_score
    )

    # Clamp to 0-100
    readiness = max(0.0, min(100.0, readiness))

    _LOGGER.debug(
        "Readiness breakdown: TSB=%.1f, Monotony=%.1f, Rest=%.1f, Load=%.1f -> Total=%.1f",
        tsb_score,
        monotony_score,
        rest_score,
        load_score,
        readiness,
    )

    return round(readiness, 1)


def _calculate_tsb_component(tsb: float) -> float:
    """Calculate TSB contribution to readiness (0-100).

    Optimal TSB range is -5 to +10 for training readiness.
    Very negative TSB (fatigue) or very positive TSB (detraining) both reduce readiness.
    """
    if -5 <= tsb <= 10:
        # Optimal zone: high readiness
        # Peak at TSB=+5
        score = 100.0 - abs(tsb - 5) * 2.0
    elif -15 <= tsb < -5:
        # Moderate fatigue: declining readiness
        score = 80.0 - (abs(tsb + 5) * 4.0)
    elif tsb < -15:
        # High fatigue: low readiness
        score = max(0.0, 40.0 - (abs(tsb + 15) * 2.0))
    elif 10 < tsb <= 20:
        # Too fresh: slightly declining readiness
        score = 90.0 - ((tsb - 10) * 3.0)
    else:
        # Very fresh (tsb > 20): risk of detraining
        score = max(30.0, 60.0 - ((tsb - 20) * 2.0))

    return max(0.0, min(100.0, score))


def _calculate_monotony_component(monotony: float) -> float:
    """Calculate monotony contribution to readiness (0-100).

    Lower monotony (more training variety) is better for long-term adaptation.
    Monotony typically ranges from 0 (max variety) to 10+ (very monotonous).
    """
    if monotony <= 0:
        # No data or zero monotony
        return 50.0

    if monotony < 3:
        # Good variety
        score = 100.0
    elif monotony < 5:
        # Moderate variety — penalize more strongly
        score = 80.0 - ((monotony - 3) * 20.0)  # 4.0 -> 60, 5.0 -> 40
    elif monotony < 8:
        # High monotony — stronger penalty
        score = max(10.0, 40.0 - ((monotony - 5) * 10.0))  # 8.0 -> 10
    else:
        # Very high monotony
        score = 10.0

    return max(0.0, min(100.0, score))


def _calculate_rest_component(rest_days: int) -> float:
    """Calculate rest days contribution to readiness (0-100).

    Optimal is 1-2 rest days in recent history.
    0 rest days (consecutive training) or 3+ rest days (too much rest) both reduce readiness.
    """
    if rest_days == 1:
        # Ideal: 1 rest day
        return 100.0
    elif rest_days == 2:
        # Good: 2 rest days
        return 90.0
    elif rest_days == 0:
        # No rest: penalize more to reflect fatigue risk
        return 50.0
    elif rest_days == 3:
        # Too much rest
        return 60.0
    elif rest_days >= 4:
        # Extended rest: declining readiness
        return max(30.0, 60.0 - ((rest_days - 3) * 10.0))
    else:
        # Fallback
        return 50.0


def _calculate_load_ratio_component(atl: float, ctl: float) -> float:
    """Calculate ATL/CTL ratio contribution to readiness (0-100).

    Ratio indicates training ramp rate:
    - < 0.8: Detraining or recovering
    - 0.8-1.0: Maintaining
    - 1.0-1.5: Building fitness
    - > 1.5: High risk of overreaching
    """
    if ctl <= 0:
        return 50.0

    ratio = atl / ctl

    if 0.9 <= ratio <= 1.2:
        # Optimal training zone
        score = 100.0
    elif 0.8 <= ratio < 0.9:
        # Slightly undertrained
        score = 80.0 + ((ratio - 0.8) * 200.0)
    elif 1.2 < ratio <= 1.5:
        # Ramping up — stronger penalty for aggressive ramp
        score = max(40.0, 70.0 - ((ratio - 1.2) * 80.0))  # 1.5 -> ~46
    elif ratio < 0.8:
        # Significant detraining
        score = max(40.0, 80.0 - ((0.8 - ratio) * 100.0))
    else:
        # High overreaching risk (ratio > 1.5)
        score = max(10.0, 50.0 - ((ratio - 1.5) * 80.0))

    return max(0.0, min(100.0, score))


def interpret_readiness(readiness: float) -> str:
    """Interpret readiness score into a readable state.

    Args:
        readiness: Score from 0-100

    Returns:
        Human-readable interpretation
    """
    if readiness >= 80:
        return "Excellent - ready for hard training"
    elif readiness >= 60:
        return "Good - ready for moderate training"
    elif readiness >= 40:
        return "Fair - consider easy training or rest"
    elif readiness >= 20:
        return "Low - prioritize recovery"
    else:
        return "Very Low - rest required"
