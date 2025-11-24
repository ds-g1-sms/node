import pytest
import asyncio
import json
import websockets
from websockets import serve

@pytest.mark.asyncio
async def test_list_rooms_protocol():
    fake_response = {
        "type": "rooms_list",
        "data": {
            "rooms": [{"room_id": "1", "room_name": "General", "description": "General chat", "member_count": 10, "admin_node": "node1"}],
            "total_count": 1
        }
    }

    async def handler(ws):
        message = await ws.recv()
        assert json.loads(message)["type"] == "list_rooms"
        await ws.send(json.dumps(fake_response))

    # Start in-memory WebSocket server
    async with serve(handler, "localhost", 9999):
        async with websockets.connect("ws://localhost:9999") as ws:
            await ws.send(json.dumps({"type": "list_rooms"}))
            response = await ws.recv()
            data = json.loads(response)

            assert data["type"] == "rooms_list"
            assert data["data"]["total_count"] == 1
            assert data["data"]["rooms"][0]["room_name"] == "General"
