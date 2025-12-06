"""Tests for SuggestionEngine."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from app.services.learning.suggestion_engine import SuggestionEngine


@pytest.fixture
def mock_db_service():
    """Fixture providing mock DatabaseService."""
    db = MagicMock()
    db.pool = MagicMock()  # Simulate connection pool exists
    return db


@pytest.fixture
def suggestion_engine(mock_db_service):
    """Fixture providing SuggestionEngine with mock database."""
    return SuggestionEngine(db_service=mock_db_service)


class TestSuggestionEngine:
    """Test suite for SuggestionEngine."""

    @pytest.mark.asyncio
    async def test_get_suggestions_returns_list(self, suggestion_engine):
        """Test get_suggestions returns a list."""
        suggestions = await suggestion_engine.get_suggestions()

        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_get_suggestions_respects_limit(self, suggestion_engine):
        """Test get_suggestions respects the limit parameter."""
        suggestions = await suggestion_engine.get_suggestions(limit=2)

        assert len(suggestions) <= 2

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_morning_suggestions(self, mock_datetime, suggestion_engine):
        """Test morning time suggestions (6-9am)."""
        # Mock morning time (7:30 AM)
        mock_now = MagicMock()
        mock_now.hour = 7
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions()

        # Should include morning-related suggestion
        assert any("morning" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_evening_suggestions(self, mock_datetime, suggestion_engine):
        """Test evening time suggestions (18-22pm)."""
        # Mock evening time (8:00 PM)
        mock_now = MagicMock()
        mock_now.hour = 20
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions()

        # Should include evening-related suggestion
        assert any("evening" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_night_suggestions(self, mock_datetime, suggestion_engine):
        """Test night time suggestions (22-24pm)."""
        # Mock night time (11:00 PM)
        mock_now = MagicMock()
        mock_now.hour = 23
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions()

        # Should include night-related suggestion
        assert any("night" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_bedroom_night_suggestions(self, mock_datetime, suggestion_engine):
        """Test bedroom-specific suggestions at night."""
        # Mock night time (11:00 PM)
        mock_now = MagicMock()
        mock_now.hour = 23
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions(room_id="sypialnia")

        # Should include bedroom-specific suggestion
        assert any("bedroom" in s.lower() or "dim" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_kitchen_morning_suggestions(self, mock_datetime, suggestion_engine):
        """Test kitchen-specific suggestions in the morning."""
        # Mock morning time (7:30 AM)
        mock_now = MagicMock()
        mock_now.hour = 7
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions(room_id="kuchnia")

        # Should include kitchen-specific suggestion
        assert any("kitchen" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_get_suggestions_without_database(self):
        """Test suggestions work without database (default suggestions)."""
        engine = SuggestionEngine(db_service=None)

        suggestions = await engine.get_suggestions()

        # Should return default suggestions
        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_get_suggestions_with_zero_limit(self, suggestion_engine):
        """Test get_suggestions with limit of 0."""
        suggestions = await suggestion_engine.get_suggestions(limit=0)

        assert suggestions == []

    @pytest.mark.asyncio
    async def test_get_default_suggestions_structure(self, suggestion_engine):
        """Test default suggestions are properly formatted."""
        suggestions = suggestion_engine._get_default_suggestions(room_id=None, limit=3)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 3
        # Each suggestion should be a string
        for suggestion in suggestions:
            assert isinstance(suggestion, str)

    @pytest.mark.asyncio
    async def test_get_default_suggestions_with_room(self, suggestion_engine):
        """Test default suggestions include room-specific ones."""
        suggestions = suggestion_engine._get_default_suggestions(room_id="salon", limit=5)

        assert isinstance(suggestions, list)
        # Should have suggestions (room-specific or general)
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_exception_handling(self, suggestion_engine):
        """Test graceful handling of exceptions."""
        # Make datetime.now() raise an exception
        with patch("app.services.learning.suggestion_engine.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("Time error")

            # Should not raise exception, should return default suggestions
            suggestions = await suggestion_engine.get_suggestions()

            assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    @patch("app.services.learning.suggestion_engine.datetime")
    async def test_midday_no_time_suggestions(self, mock_datetime, suggestion_engine):
        """Test midday time has no specific time-based suggestions."""
        # Mock midday time (1:00 PM)
        mock_now = MagicMock()
        mock_now.hour = 13
        mock_datetime.now.return_value = mock_now

        suggestions = await suggestion_engine.get_suggestions()

        # Should not include morning/evening/night suggestions
        assert not any("morning" in s.lower() for s in suggestions)
        assert not any("evening" in s.lower() for s in suggestions)
        assert not any("night" in s.lower() for s in suggestions)

    @pytest.mark.asyncio
    async def test_suggestions_are_unique(self, suggestion_engine):
        """Test returned suggestions don't contain duplicates."""
        suggestions = await suggestion_engine.get_suggestions(limit=10)

        # Check for unique suggestions
        assert len(suggestions) == len(set(suggestions))
