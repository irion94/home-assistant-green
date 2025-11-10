"""Metrics package for Strava Coach."""

from __future__ import annotations

from .ctl_atl_tsb import (
    FitnessMetrics,
    calculate_atl_ctl_tsb,
    calculate_metrics_incremental,
    interpret_tsb,
)
from .readiness import calculate_readiness, interpret_readiness
from .stress import calculate_training_load
from .suggest_rules import TrainingSuggestion, generate_suggestion, suggest_for_date

__all__ = [
    "FitnessMetrics",
    "TrainingSuggestion",
    "calculate_atl_ctl_tsb",
    "calculate_metrics_incremental",
    "calculate_readiness",
    "calculate_training_load",
    "generate_suggestion",
    "interpret_readiness",
    "interpret_tsb",
    "suggest_for_date",
]
