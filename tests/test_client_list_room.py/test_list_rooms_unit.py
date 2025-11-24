import pytest
import asyncio
import json
from unittest.mock import AsyncMock
from src.client.main import list_rooms

@pytest.mark.asyncio
async def test_list_rooms_unit(monkeypatch):
    # Fake WebSocket
    fake_ws = AsyncMock()
    fake_response = {
        "type": "rooms_list",
        "data": {
            "rooms": [{"room_id": "1", "room_name": "General", "description": "General chat", "member_count": 10, "admin_node": "node1"}],
            "total_count": 1
        }
    }

    # recv() should return a string directly
    fake_ws.recv.return_value = json.dumps(fake_response)

    # Make the mock support `async with`
    fake_connect_cm = AsyncMock()
    fake_connect_cm.__aenter__.return_value = fake_ws
    fake_connect_cm.__aexit__.return_value = None

    # Patch websockets.connect
    monkeypatch.setattr("websockets.connect", lambda uri: fake_connect_cm)

    # Call the actual function
    await list_rooms()

    # Ensure the client sent the correct request
    fake_ws.send.assert_called_with(json.dumps({"type": "list_rooms"}))
