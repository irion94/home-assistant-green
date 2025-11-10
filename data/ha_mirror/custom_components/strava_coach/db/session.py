"""Database session management for Strava Coach."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_LOGGER = logging.getLogger(__name__)

_engine: Any = None
_session_factory: Any = None


def init_db(db_path: str) -> None:
    """Initialize the database.

    Args:
        db_path: Path to SQLite database file
    """
    global _engine, _session_factory

    _LOGGER.info("Initializing database at %s", db_path)

    # Create engine
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create tables
    Base.metadata.create_all(_engine)

    # Create session factory
    _session_factory = sessionmaker(bind=_engine)

    _LOGGER.info("Database initialized successfully")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session.

    Yields:
        SQLAlchemy session

    Example:
        with get_session() as session:
            activities = session.query(Activity).all()
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    session: Session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()
        _engine = None
        _session_factory = None
        _LOGGER.info("Database connections closed")
