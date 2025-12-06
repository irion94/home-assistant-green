import pytest
from fastapi.testclient import TestClient


def test_conversation_endpoint(client: TestClient, mock_ha_client):
    """Test /conversation endpoint."""
    response = client.post(
        "/conversation",
        json={
            "text": "Turn on living room lights",
            "session_id": "test-session",
            "room_id": "living_room",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "session_id" in data


@pytest.mark.asyncio
async def test_conversation_with_tools(mock_ha_client, mock_mqtt_client):
    """Test conversation with tool execution."""
    from app.services.conversation_client import ConversationClient

    client = ConversationClient(
        ha_client=mock_ha_client,
        mqtt_client=mock_mqtt_client,
    )

    response = await client.chat(
        "Turn on all lights",
        session_id="test",
        room_id="living_room",
    )

    assert response is not None
    assert mock_ha_client.call_service.called
