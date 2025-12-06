"""Tests for MediaControlTool."""

import pytest
from unittest.mock import AsyncMock
from app.services.tools.media_control_tool import MediaControlTool


@pytest.fixture
def media_control_tool(mock_ha_client):
    """Fixture providing MediaControlTool instance."""
    return MediaControlTool(ha_client=mock_ha_client)


class TestMediaControlTool:
    """Test suite for MediaControlTool."""

    def test_tool_name(self, media_control_tool):
        """Test tool name is correct."""
        assert media_control_tool.name == "control_media"

    def test_schema_structure(self, media_control_tool):
        """Test schema has required OpenAI structure."""
        schema = media_control_tool.schema
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "control_media"
        assert "parameters" in schema["function"]

    def test_schema_required_params(self, media_control_tool):
        """Test schema requires 'action' and 'entity_id' parameters."""
        schema = media_control_tool.schema
        params = schema["function"]["parameters"]
        assert "action" in params["properties"]
        assert "entity_id" in params["properties"]
        assert "action" in params["required"]
        assert "entity_id" in params["required"]

    def test_schema_action_enum(self, media_control_tool):
        """Test schema includes all valid media actions."""
        schema = media_control_tool.schema
        actions = schema["function"]["parameters"]["properties"]["action"]["enum"]
        assert "play" in actions
        assert "pause" in actions
        assert "toggle" in actions
        assert "next" in actions
        assert "previous" in actions
        assert "volume_up" in actions
        assert "volume_down" in actions
        assert "volume_set" in actions

    @pytest.mark.asyncio
    async def test_missing_action_parameter(self, media_control_tool):
        """Test missing action parameter fails."""
        result = await media_control_tool.execute(
            arguments={"entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "missing" in result.content.lower() or "required" in result.content.lower()

    @pytest.mark.asyncio
    async def test_missing_entity_id_parameter(self, media_control_tool):
        """Test missing entity_id parameter fails."""
        result = await media_control_tool.execute(
            arguments={"action": "play"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_successful_play_action(self, media_control_tool, mock_ha_client):
        """Test successful play action."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "playing",
            "attributes": {
                "friendly_name": "Spotify",
                "media_title": "Test Song",
                "media_artist": "Test Artist",
                "volume_level": 0.5
            }
        })

        result = await media_control_tool.execute(
            arguments={"action": "play", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert mock_ha_client.call_service.called

    @pytest.mark.asyncio
    async def test_successful_pause_action(self, media_control_tool, mock_ha_client):
        """Test successful pause action."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "paused",
            "attributes": {"friendly_name": "Music Player"}
        })

        result = await media_control_tool.execute(
            arguments={"action": "pause", "entity_id": "media_player.music"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_volume_set_action(self, media_control_tool, mock_ha_client):
        """Test volume_set action with volume_level parameter."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "playing",
            "attributes": {"volume_level": 0.7}
        })

        result = await media_control_tool.execute(
            arguments={
                "action": "volume_set",
                "entity_id": "media_player.spotify",
                "volume_level": 0.7
            },
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_display_action_structure(self, media_control_tool, mock_ha_client):
        """Test display action is correctly formatted."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "playing",
            "attributes": {
                "friendly_name": "Spotify",
                "media_title": "Song Title",
                "media_artist": "Artist Name",
                "media_album_name": "Album",
                "entity_picture": "/local/artwork.jpg",
                "volume_level": 0.6,
                "media_duration": 240,
                "media_position": 60
            }
        })

        result = await media_control_tool.execute(
            arguments={"action": "play", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.display_action is not None
        assert result.display_action["type"] == "media_control"
        data = result.display_action["data"]
        assert data["entity_id"] == "media_player.spotify"
        assert "now_playing" in data
        assert data["now_playing"]["title"] == "Song Title"
        assert data["now_playing"]["artist"] == "Artist Name"

    @pytest.mark.asyncio
    async def test_next_track_action(self, media_control_tool, mock_ha_client):
        """Test next track action."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "playing",
            "attributes": {"friendly_name": "Player"}
        })

        result = await media_control_tool.execute(
            arguments={"action": "next", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True
        assert mock_ha_client.call_service.called

    @pytest.mark.asyncio
    async def test_previous_track_action(self, media_control_tool, mock_ha_client):
        """Test previous track action."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value={
            "state": "playing",
            "attributes": {"friendly_name": "Player"}
        })

        result = await media_control_tool.execute(
            arguments={"action": "previous", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_ha_call_failure(self, media_control_tool, mock_ha_client):
        """Test handling HA service call failure."""
        mock_ha_client.call_service = AsyncMock(return_value=None)

        result = await media_control_tool.execute(
            arguments={"action": "play", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_entity_state_fetch_failure(self, media_control_tool, mock_ha_client):
        """Test handling when entity state fetch fails."""
        mock_ha_client.call_service = AsyncMock(return_value={"success": True})
        mock_ha_client.get_state = AsyncMock(return_value=None)

        result = await media_control_tool.execute(
            arguments={"action": "play", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        # Should succeed but with minimal display data
        assert result.success is True

    @pytest.mark.asyncio
    async def test_exception_handling(self, media_control_tool, mock_ha_client):
        """Test exception during media control is caught."""
        mock_ha_client.call_service = AsyncMock(side_effect=Exception("Connection error"))

        result = await media_control_tool.execute(
            arguments={"action": "play", "entity_id": "media_player.spotify"},
            room_id="test_room",
            session_id="test_session"
        )

        assert result.success is False
        assert "error" in result.content.lower() or "failed" in result.content.lower()
