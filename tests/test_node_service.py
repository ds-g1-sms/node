import json
import pytest
import pytest_asyncio

from src.node.service import NodeService
from src.node.state import NodeState


# ----------------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------------

class MockWebSocket:
    """Simple mock websocket that records sent messages."""
    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


@pytest_asyncio.fixture
async def node_service():
    state = NodeState()
    return NodeService(node_id="node-1", state=state)


@pytest_asyncio.fixture
async def websocket():
    return MockWebSocket()


# ----------------------------------------------------------------------------
# Test handle_message()
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_message_invalid_json(node_service, websocket):
    await node_service.handle_message(websocket, "not-json")

    msg = json.loads(websocket.sent_messages[0])
    assert msg["type"] == "error"
    assert msg["data"]["error_code"] == "invalid_json"


@pytest.mark.asyncio
async def test_handle_message_unknown_type(node_service, websocket):
    payload = {
        "type": "unknown",
        "data": {}
    }
    await node_service.handle_message(websocket, json.dumps(payload))

    msg = json.loads(websocket.sent_messages[0])
    assert msg["type"] == "error"
    assert msg["data"]["error_code"] == "unknown_type"
    assert "unknown" in msg["data"]["message"]


# ----------------------------------------------------------------------------
# Test room creation
# ----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_room_success(node_service, websocket):
    payload = {
        "type": "create_room_request",
        "data": {
            "room_name": "RoomA",
            "creator_id": "user123",
            "description": "Test room"
        }
    }

    await node_service.handle_message(websocket, json.dumps(payload))
