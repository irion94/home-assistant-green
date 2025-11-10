"""Database models for Strava Coach."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Activity(Base):
    """Strava activity model."""

    __tablename__ = "activities"

    id = Column(BigInteger, primary_key=True)  # Strava activity ID
    athlete_id = Column(BigInteger, nullable=False, index=True)
    name = Column(String, nullable=False)
    sport_type = Column(String, nullable=False)  # e.g., "Ride", "Run", "Swim"
    start_date = Column(DateTime, nullable=False, index=True)
    start_date_local = Column(DateTime, nullable=False)
    timezone = Column(String, nullable=True)

    # Duration and distance
    moving_time = Column(Integer, nullable=False)  # seconds
    elapsed_time = Column(Integer, nullable=False)  # seconds
    distance = Column(Float, nullable=False)  # meters

    # Elevation
    total_elevation_gain = Column(Float, nullable=True)  # meters

    # Intensity metrics
    average_heartrate = Column(Float, nullable=True)  # bpm
    max_heartrate = Column(Float, nullable=True)  # bpm
    average_watts = Column(Float, nullable=True)
    weighted_average_watts = Column(Float, nullable=True)  # Normalized Power
    kilojoules = Column(Float, nullable=True)

    # Computed training metrics
    training_load = Column(Float, nullable=True)  # TRIMP-like stress score
    intensity_factor = Column(Float, nullable=True)  # IF (watts/FTP)

    # Raw data for debugging (minimal, aggregated only)
    summary_data = Column(JSON, nullable=True)

    # Sync metadata
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Activity {self.id}: {self.name} ({self.sport_type}) on {self.start_date}>"


class DailyMetrics(Base):
    """Daily computed metrics (ATL, CTL, TSB, Readiness)."""

    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(BigInteger, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    # Fitness metrics
    atl = Column(Float, nullable=False)  # Acute Training Load (7-day EWMA)
    ctl = Column(Float, nullable=False)  # Chronic Training Load (42-day EWMA)
    tsb = Column(Float, nullable=False)  # Training Stress Balance (Form)

    # Additional metrics
    monotony = Column(Float, nullable=True)  # Training monotony index
    readiness = Column(Float, nullable=False)  # 0-100 readiness score

    # Context
    rest_days = Column(Integer, nullable=True)  # Consecutive rest days
    weekly_load = Column(Float, nullable=True)  # Total load in last 7 days

    # Computed metadata
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<DailyMetrics {self.athlete_id} on {self.date}: ATL={self.atl:.1f}, CTL={self.ctl:.1f}, TSB={self.tsb:.1f}, Readiness={self.readiness:.0f}>"


class SyncState(Base):
    """Track synchronization state."""

    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    athlete_id = Column(BigInteger, nullable=False, unique=True, index=True)

    # Sync timestamps
    last_sync_at = Column(DateTime, nullable=True)
    last_activity_date = Column(DateTime, nullable=True)  # Date of most recent activity
    next_sync_at = Column(DateTime, nullable=True)

    # Sync metadata
    total_activities = Column(Integer, default=0, nullable=False)
    sync_errors = Column(Integer, default=0, nullable=False)
    last_error = Column(String, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<SyncState {self.athlete_id}: last_sync={self.last_sync_at}, activities={self.total_activities}>"
