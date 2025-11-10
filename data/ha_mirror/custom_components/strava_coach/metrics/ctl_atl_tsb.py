"""Calculate ATL, CTL, and TSB fitness metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


@dataclass
class FitnessMetrics:
    """Container for fitness metrics."""

    atl: float  # Acute Training Load (fatigue)
    ctl: float  # Chronic Training Load (fitness)
    tsb: float  # Training Stress Balance (form)
    monotony: float  # Training monotony index


def calculate_ewma(
    current_value: float,
    previous_ewma: float,
    time_constant: int,
) -> float:
    """Calculate Exponentially Weighted Moving Average.

    Args:
        current_value: Today's training load
        previous_ewma: Previous EWMA value
        time_constant: Time constant in days (e.g., 7 for ATL, 42 for CTL)

    Returns:
        Updated EWMA value
    """
    if time_constant <= 0:
        return current_value

    # Smoothing factor
    alpha = 2.0 / (time_constant + 1)

    # EWMA = alpha × current + (1 - alpha) × previous
    ewma = alpha * current_value + (1 - alpha) * previous_ewma

    return ewma


def calculate_atl_ctl_tsb(
    daily_loads: list[tuple[datetime, float]],
    atl_days: int = 7,
    ctl_days: int = 42,
) -> dict[datetime, FitnessMetrics]:
    """Calculate ATL, CTL, and TSB for a series of daily training loads.

    Args:
        daily_loads: List of (date, training_load) tuples, sorted by date
        atl_days: Time constant for ATL (Acute Training Load), default 7 days
        ctl_days: Time constant for CTL (Chronic Training Load), default 42 days

    Returns:
        Dictionary mapping date to FitnessMetrics
    """
    if not daily_loads:
        return {}

    result: dict[datetime, FitnessMetrics] = {}

    # Sort by date to ensure chronological processing
    sorted_loads = sorted(daily_loads, key=lambda x: x[0])

    # Initialize with first day
    first_date, first_load = sorted_loads[0]
    atl = first_load
    ctl = first_load
    tsb = ctl - atl

    result[first_date] = FitnessMetrics(
        atl=atl,
        ctl=ctl,
        tsb=tsb,
        monotony=0.0,  # Not enough data for monotony yet
    )

    # Process each subsequent day
    for i in range(1, len(sorted_loads)):
        date, load = sorted_loads[i]

        # Update ATL and CTL using EWMA
        atl = calculate_ewma(load, atl, atl_days)
        ctl = calculate_ewma(load, ctl, ctl_days)

        # Calculate TSB (Form)
        tsb = ctl - atl

        # Calculate monotony (standard deviation of last 7 days)
        monotony = 0.0
        if i >= 7:
            last_7_loads = [l for _, l in sorted_loads[i - 6 : i + 1]]
            mean_load = sum(last_7_loads) / len(last_7_loads)
            variance = sum((l - mean_load) ** 2 for l in last_7_loads) / len(last_7_loads)
            std_dev = variance**0.5

            # Monotony = mean / std_dev (higher = more monotonous)
            # Invert so higher = more variety
            if std_dev > 0:
                monotony = mean_load / std_dev
            else:
                monotony = 0.0  # All same = max monotony

        result[date] = FitnessMetrics(
            atl=atl,
            ctl=ctl,
            tsb=tsb,
            monotony=monotony,
        )

    return result


def calculate_metrics_incremental(
    current_atl: float,
    current_ctl: float,
    today_load: float,
    atl_days: int = 7,
    ctl_days: int = 42,
) -> FitnessMetrics:
    """Calculate today's metrics incrementally from previous values.

    This is more efficient when you only need today's metrics and have yesterday's values.

    Args:
        current_atl: Yesterday's ATL
        current_ctl: Yesterday's CTL
        today_load: Today's training load
        atl_days: Time constant for ATL
        ctl_days: Time constant for CTL

    Returns:
        Today's FitnessMetrics
    """
    # Update ATL and CTL
    new_atl = calculate_ewma(today_load, current_atl, atl_days)
    new_ctl = calculate_ewma(today_load, current_ctl, ctl_days)

    # Calculate TSB
    tsb = new_ctl - new_atl

    return FitnessMetrics(
        atl=new_atl,
        ctl=new_ctl,
        tsb=tsb,
        monotony=0.0,  # Would need historical data to compute
    )


def interpret_tsb(tsb: float) -> str:
    """Interpret TSB value into a readable form/recovery state.

    Args:
        tsb: Training Stress Balance value

    Returns:
        Human-readable interpretation
    """
    if tsb < -30:
        return "Very fatigued - high risk of overtraining"
    elif tsb < -10:
        return "Fatigued - need recovery"
    elif tsb < 5:
        return "Maintaining - good training state"
    elif tsb < 15:
        return "Fresh - optimal for racing"
    else:
        return "Very fresh - risk of detraining"
