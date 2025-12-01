"""Tests for ContextEngine."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.learning.context_engine import ContextEngine


@pytest.fixture
def mock_db_service():
    """Fixture providing mock DatabaseService."""
    db = MagicMock()
    db.pool = MagicMock()  # Simulate connection pool exists
    db.get_conversation_history = AsyncMock(return_value=[])
    db.get_preferences_by_category = AsyncMock(return_value={})
    return db


@pytest.fixture
def context_engine(mock_db_service):
    """Fixture providing ContextEngine with mock database."""
    return ContextEngine(db_service=mock_db_service)


class TestContextEngine:
    """Test suite for ContextEngine."""

    @pytest.mark.asyncio
    async def test_get_context_structure(self, context_engine):
        """Test context has expected structure."""
        context = await context_engine.get_context(
            session_id="test_session",
            room_id="living_room"
        )

        assert "conversation_history" in context
        assert "preferences" in context
        assert "room_context" in context
        assert "metadata" in context
        assert context["metadata"]["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_get_context_with_room_id(self, context_engine):
        """Test room context is included when room_id provided."""
        context = await context_engine.get_context(
            session_id="test_session",
            room_id="bedroom"
        )

        assert context["room_context"]["room_id"] == "bedroom"

    @pytest.mark.asyncio
    async def test_get_context_without_room_id(self, context_engine):
        """Test context works without room_id."""
        context = await context_engine.get_context(session_id="test_session")

        assert "room_context" in context
        # Room context should be empty dict without room_id
        assert context["room_context"] == {}

    @pytest.mark.asyncio
    async def test_get_context_retrieves_history(self, context_engine, mock_db_service):
        """Test conversation history is retrieved from database."""
        mock_history = [
            {"user": "Turn on lights", "assistant": "Done"},
            {"user": "What's the time?", "assistant": "3:00 PM"}
        ]
        mock_db_service.get_conversation_history = AsyncMock(return_value=mock_history)

        context = await context_engine.get_context(session_id="test_session", limit=10)

        assert context["conversation_history"] == mock_history
        mock_db_service.get_conversation_history.assert_called_once_with(
            session_id="test_session",
            limit=10
        )

    @pytest.mark.asyncio
    async def test_get_context_retrieves_preferences(self, context_engine, mock_db_service):
        """Test user preferences are retrieved from database."""
        mock_prefs = {"theme": "dark", "language": "en"}
        mock_db_service.get_preferences_by_category = AsyncMock(return_value=mock_prefs)

        context = await context_engine.get_context(session_id="test_session")

        assert context["preferences"] == mock_prefs
        mock_db_service.get_preferences_by_category.assert_called_once_with("user")

    @pytest.mark.asyncio
    async def test_get_context_handles_db_unavailable(self):
        """Test graceful handling when database is unavailable."""
        # Create context engine with no database
        context_engine = ContextEngine(db_service=None)

        context = await context_engine.get_context(session_id="test_session")

        # Should return empty context structure
        assert context["conversation_history"] == []
        assert context["preferences"] == {}
        assert context["metadata"]["session_id"] == "test_session"

    @pytest.mark.asyncio
    async def test_get_context_handles_history_error(self, context_engine, mock_db_service):
        """Test graceful handling when history retrieval fails."""
        mock_db_service.get_conversation_history = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Should not raise exception
        context = await context_engine.get_context(session_id="test_session")

        # Should still return context with empty history
        assert "conversation_history" in context
        assert "metadata" in context

    @pytest.mark.asyncio
    async def test_get_context_handles_preferences_error(self, context_engine, mock_db_service):
        """Test graceful handling when preferences retrieval fails."""
        mock_db_service.get_preferences_by_category = AsyncMock(
            side_effect=Exception("Preferences error")
        )

        # Should not raise exception
        context = await context_engine.get_context(session_id="test_session")

        # Should return context with empty preferences
        assert context["preferences"] == {}

    @pytest.mark.asyncio
    async def test_learn_pattern_stores_in_database(self, context_engine, mock_db_service):
        """Test pattern learning stores data in database."""
        mock_db_service.store_training_data = AsyncMock(return_value=True)

        await context_engine.learn_pattern(
            user_input="Turn on the lights",
            intent="control_light",
            session_id="test_session"
        )

        # Should call database to store pattern
        mock_db_service.store_training_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_learn_pattern_handles_db_unavailable(self):
        """Test pattern learning gracefully handles no database."""
        context_engine = ContextEngine(db_service=None)

        # Should not raise exception
        await context_engine.learn_pattern(
            user_input="Turn on lights",
            intent="control_light",
            session_id="test_session"
        )

    @pytest.mark.asyncio
    async def test_get_patterns_for_intent(self, context_engine, mock_db_service):
        """Test retrieving learned patterns for an intent."""
        mock_patterns = [
            "Turn on the lights",
            "Switch on lights",
            "Enable lighting"
        ]
        mock_db_service.get_patterns_for_intent = AsyncMock(return_value=mock_patterns)

        patterns = await context_engine.get_patterns_for_intent("control_light")

        assert patterns == mock_patterns
        mock_db_service.get_patterns_for_intent.assert_called_once_with("control_light")

    @pytest.mark.asyncio
    async def test_get_context_with_custom_limit(self, context_engine, mock_db_service):
        """Test context retrieval respects custom history limit."""
        context = await context_engine.get_context(session_id="test_session", limit=5)

        mock_db_service.get_conversation_history.assert_called_once_with(
            session_id="test_session",
            limit=5
        )
