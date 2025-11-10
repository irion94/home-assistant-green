"""Tests for metrics calculation."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from custom_components.strava_coach.metrics import (
    calculate_atl_ctl_tsb,
    calculate_readiness,
    calculate_training_load,
    generate_suggestion,
)


class TestTrainingLoad:
    """Test training load calculation."""

    def test_power_based_load(self) -> None:
        """Test TSS calculation from power data."""
        activity = {
            "moving_time": 3600,  # 1 hour
            "average_watts": 250,
            "weighted_average_watts": 260,
            "sport_type": "Ride",
        }

        load = calculate_training_load(activity)

        # For 1 hour at FTP (250W default), IF=1.04, TSS should be ~108
        assert 100 < load < 120

    def test_hr_based_load(self) -> None:
        """Test TRIMP calculation from heart rate data."""
        activity = {
            "moving_time": 3600,  # 1 hour
            "average_heartrate": 150,
            "max_heartrate": 175,
            "sport_type": "Run",
        }

        load = calculate_training_load(activity)

        # 1 hour at moderate HR should give reasonable TRIMP
        assert 50 < load < 150

    def test_fallback_load(self) -> None:
        """Test fallback calculation without HR or power."""
        activity = {
            "moving_time": 3600,  # 1 hour
            "distance": 30000,  # 30km
            "total_elevation_gain": 500,  # 500m
            "sport_type": "Ride",
        }

        load = calculate_training_load(activity)

        # Should produce a reasonable estimate
        assert 30 < load < 150

    def test_zero_activity(self) -> None:
        """Test with zero duration activity."""
        activity = {
            "moving_time": 0,
            "sport_type": "Ride",
        }

        load = calculate_training_load(activity)

        assert load == 0.0


class TestATLCTLTSB:
    """Test ATL, CTL, and TSB calculations."""

    def test_consistent_training(self) -> None:
        """Test with consistent daily training load."""
        # 30 days of consistent 100 TSS
        start_date = datetime(2025, 1, 1)
        daily_loads = [
            (start_date + timedelta(days=i), 100.0) for i in range(30)
        ]

        metrics = calculate_atl_ctl_tsb(daily_loads)

        # After 30 days of consistent load, ATL and CTL should stabilize
        final_metrics = metrics[start_date + timedelta(days=29)]

        # ATL (7-day EWMA) should be close to 100
        assert 85 < final_metrics.atl < 105

        # CTL (42-day EWMA) should approach 100 but slower
        assert 60 < final_metrics.ctl < 100

        # TSB should be negative (fatigue) since ATL > CTL
        assert final_metrics.tsb < 0

    def test_rest_day(self) -> None:
        """Test TSB increase with rest day."""
        start_date = datetime(2025, 1, 1)

        # 20 days of training, then 3 rest days
        daily_loads = [(start_date + timedelta(days=i), 100.0) for i in range(20)]
        daily_loads.extend([(start_date + timedelta(days=i), 0.0) for i in range(20, 23)])

        metrics = calculate_atl_ctl_tsb(daily_loads)

        # TSB should increase (become less negative) during rest
        tsb_before_rest = metrics[start_date + timedelta(days=19)].tsb
        tsb_after_rest = metrics[start_date + timedelta(days=22)].tsb

        assert tsb_after_rest > tsb_before_rest

    def test_increasing_load(self) -> None:
        """Test progressive overload."""
        start_date = datetime(2025, 1, 1)

        # Progressive increase: 50, 60, 70, ..., 150 TSS
        daily_loads = [
            (start_date + timedelta(days=i), 50.0 + i * 10) for i in range(11)
        ]

        metrics = calculate_atl_ctl_tsb(daily_loads)

        # CTL should increase over time
        ctl_start = metrics[start_date].ctl
        ctl_end = metrics[start_date + timedelta(days=10)].ctl

        assert ctl_end > ctl_start


class TestReadiness:
    """Test readiness score calculation."""

    def test_optimal_readiness(self) -> None:
        """Test readiness with optimal metrics."""
        readiness = calculate_readiness(
            tsb=5.0,  # Optimal form
            monotony=2.5,  # Good variety
            rest_days=1,  # Ideal rest
            atl=80.0,
            ctl=85.0,
        )

        # Should be high readiness
        assert readiness > 80

    def test_fatigued_readiness(self) -> None:
        """Test readiness when fatigued."""
        readiness = calculate_readiness(
            tsb=-25.0,  # High fatigue
            monotony=4.0,
            rest_days=0,  # No rest
            atl=120.0,
            ctl=95.0,
        )

        # Should be low readiness
        assert readiness < 40

    def test_overtrained_readiness(self) -> None:
        """Test readiness with overtraining indicators."""
        readiness = calculate_readiness(
            tsb=-30.0,  # Very fatigued
            monotony=8.0,  # Very monotonous
            rest_days=0,
            atl=150.0,
            ctl=100.0,
        )

        # Should be very low readiness
        assert readiness < 30

    def test_detraining_readiness(self) -> None:
        """Test readiness after extended rest."""
        readiness = calculate_readiness(
            tsb=25.0,  # Too fresh
            monotony=0.0,
            rest_days=7,  # Week of rest
            atl=30.0,
            ctl=100.0,
        )

        # Should be moderate (too much rest)
        assert 40 < readiness < 70


class TestSuggestions:
    """Test rule-based suggestion generation."""

    def test_rest_suggestion_when_fatigued(self) -> None:
        """Test that REST_DAY is suggested when very fatigued."""
        suggestion = generate_suggestion(
            readiness=25.0,
            tsb=-25.0,
            atl=120.0,
            ctl=90.0,
            rest_days=0,
            recent_load_7d=700.0,
        )

        assert suggestion.command == "REST_DAY"
        assert "fatigue" in suggestion.rationale_short.lower()

    def test_intensity_suggestion_when_fresh(self) -> None:
        """Test that high intensity is suggested when fresh."""
        suggestion = generate_suggestion(
            readiness=85.0,
            tsb=10.0,
            atl=60.0,
            ctl=80.0,
            rest_days=1,
            recent_load_7d=400.0,
        )

        assert "VO2MAX" in suggestion.command or "SWEETSPOT" in suggestion.command
        assert "readiness" in suggestion.rationale_short.lower()

    def test_moderate_training_suggestion(self) -> None:
        """Test moderate training suggestion with balanced metrics."""
        suggestion = generate_suggestion(
            readiness=65.0,
            tsb=2.0,
            atl=75.0,
            ctl=77.0,
            rest_days=1,
            recent_load_7d=500.0,
        )

        # Should suggest moderate training
        assert suggestion.command in ("TEMPO_RIDE", "SWEETSPOT_3x12", "Z2_RIDE")

    def test_recovery_suggestion_after_no_rest(self) -> None:
        """Test that active recovery is suggested when needed."""
        suggestion = generate_suggestion(
            readiness=45.0,
            tsb=-12.0,
            atl=90.0,
            ctl=78.0,
            rest_days=0,
            recent_load_7d=600.0,
        )

        assert suggestion.command in ("MOBILITY_20MIN", "Z2_RIDE", "REST_DAY")
