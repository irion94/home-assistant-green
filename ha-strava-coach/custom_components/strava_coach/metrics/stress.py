"""Training stress and load calculation."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Constants for stress calculation
DEFAULT_FTP = 250  # Watts, for power-based sports
DEFAULT_THRESHOLD_HR = 165  # bpm, for HR-based sports
ELEVATION_FACTOR = 0.1  # Stress multiplier per 100m elevation


def calculate_trimp_hr(
    moving_time_seconds: int,
    average_hr: float | None,
    max_hr: float | None,
    threshold_hr: float = DEFAULT_THRESHOLD_HR,
) -> float:
    """Calculate TRIMP (Training Impulse) using heart rate.

    Args:
        moving_time_seconds: Duration of activity in seconds
        average_hr: Average heart rate (bpm)
        max_hr: Maximum heart rate during activity (bpm)
        threshold_hr: Lactate threshold heart rate (bpm)

    Returns:
        TRIMP score (0-200+ range)
    """
    if not average_hr or moving_time_seconds <= 0:
        return 0.0

    # Duration in minutes
    duration_min = moving_time_seconds / 60.0

    # HR intensity factor (normalized to threshold)
    hr_intensity = average_hr / threshold_hr

    # TRIMP = duration × intensity × intensity_multiplier
    # Using exponential weighting for higher intensities
    intensity_weight = 1.92 ** (hr_intensity - 1.0)

    trimp = duration_min * hr_intensity * intensity_weight

    return min(trimp, 500.0)  # Cap at reasonable max


def calculate_stress_power(
    moving_time_seconds: int,
    normalized_power: float | None,
    average_power: float | None,
    kilojoules: float | None,
    ftp: float = DEFAULT_FTP,
) -> float:
    """Calculate training stress using power data (similar to TSS).

    Args:
        moving_time_seconds: Duration of activity in seconds
        normalized_power: Weighted/normalized average power (watts)
        average_power: Average power (watts)
        kilojoules: Total energy expenditure
        ftp: Functional Threshold Power (watts)

    Returns:
        Training Stress Score (0-200+ range)
    """
    if moving_time_seconds <= 0:
        return 0.0

    # Prefer normalized power, fallback to average
    power = normalized_power or average_power

    if not power:
        # Estimate from kilojoules if available
        if kilojoules and moving_time_seconds > 0:
            power = (kilojoules * 1000) / moving_time_seconds
        else:
            return 0.0

    # Duration in hours
    duration_hr = moving_time_seconds / 3600.0

    # Intensity Factor (IF)
    intensity_factor = power / ftp

    # TSS = (duration × power × IF) / (FTP × 3600) × 100
    # Simplified: TSS = duration_hr × IF² × 100
    tss = duration_hr * (intensity_factor**2) * 100

    return min(tss, 500.0)  # Cap at reasonable max


def calculate_stress_fallback(
    moving_time_seconds: int,
    distance_meters: float,
    elevation_gain: float | None,
    sport_type: str,
) -> float:
    """Calculate estimated training stress without HR or power data.

    Uses duration, distance, and elevation as crude proxies.

    Args:
        moving_time_seconds: Duration of activity in seconds
        distance_meters: Distance covered (meters)
        elevation_gain: Total elevation gain (meters)
        sport_type: Type of activity ("Ride", "Run", "Swim", etc.)

    Returns:
        Estimated training stress score
    """
    if moving_time_seconds <= 0:
        return 0.0

    # Base score from duration (minutes)
    duration_min = moving_time_seconds / 60.0
    base_score = duration_min * 0.5  # Rough baseline

    # Intensity multiplier based on sport type
    sport_multipliers = {
        "Ride": 1.0,
        "Run": 1.3,  # Running is more stressful per minute
        "Swim": 0.8,
        "VirtualRide": 1.1,
        "Workout": 1.2,
        "WeightTraining": 0.9,
        "Yoga": 0.4,
    }
    multiplier = sport_multipliers.get(sport_type, 1.0)

    # Add elevation stress if available
    elevation_stress = 0.0
    if elevation_gain:
        # Each 100m of elevation adds to stress
        elevation_stress = (elevation_gain / 100.0) * ELEVATION_FACTOR * duration_min

    # Speed factor (crude intensity proxy)
    speed_factor = 1.0
    if distance_meters > 0 and moving_time_seconds > 0:
        speed_mps = distance_meters / moving_time_seconds
        # Normalize against typical speeds (e.g., 20 km/h = 5.56 m/s for cycling)
        if sport_type in ("Ride", "VirtualRide"):
            speed_factor = max(0.5, min(2.0, speed_mps / 5.56))
        elif sport_type == "Run":
            speed_factor = max(0.5, min(2.0, speed_mps / 3.33))  # ~12 km/h baseline

    total_stress = base_score * multiplier * speed_factor + elevation_stress

    return min(total_stress, 300.0)  # Lower cap since this is less accurate


def calculate_training_load(activity_data: dict[str, Any]) -> float:
    """Calculate training load for an activity using best available data.

    Priority:
    1. Power data (if available)
    2. Heart rate data (if available)
    3. Fallback estimation (duration + elevation + sport type)

    Args:
        activity_data: Activity data dict with keys like:
            - moving_time, elapsed_time
            - average_heartrate, max_heartrate
            - average_watts, weighted_average_watts, kilojoules
            - distance, total_elevation_gain
            - sport_type

    Returns:
        Training load score (0-500 range)
    """
    moving_time = activity_data.get("moving_time", 0)
    sport_type = activity_data.get("sport_type", "Workout")

    # Try power-based calculation first
    if activity_data.get("average_watts") or activity_data.get("weighted_average_watts"):
        load = calculate_stress_power(
            moving_time_seconds=moving_time,
            normalized_power=activity_data.get("weighted_average_watts"),
            average_power=activity_data.get("average_watts"),
            kilojoules=activity_data.get("kilojoules"),
        )
        if load > 0:
            _LOGGER.debug("Calculated power-based training load: %.1f", load)
            return load

    # Try HR-based calculation
    if activity_data.get("average_heartrate"):
        load = calculate_trimp_hr(
            moving_time_seconds=moving_time,
            average_hr=activity_data.get("average_heartrate"),
            max_hr=activity_data.get("max_heartrate"),
        )
        if load > 0:
            _LOGGER.debug("Calculated HR-based training load: %.1f", load)
            return load

    # Fallback to duration/distance/elevation estimation
    load = calculate_stress_fallback(
        moving_time_seconds=moving_time,
        distance_meters=activity_data.get("distance", 0.0),
        elevation_gain=activity_data.get("total_elevation_gain"),
        sport_type=sport_type,
    )
    _LOGGER.debug("Calculated fallback training load: %.1f", load)
    return load
