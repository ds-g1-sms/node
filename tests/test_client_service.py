"""
Tests for Client Service

Basic tests to verify that the client service module can be imported
and instantiated. These are minimal tests to establish test infrastructure.

Future tests should include:
    - Integration tests with a real WebSocket server
    - Mock tests for message handling
    - Protocol message serialization tests
    - Error handling tests
"""

import pytest
from src.client import ClientService, CreateRoomRequest, RoomCreatedResponse


def test_client_service_can_be_imported():
    """Test that ClientService can be imported."""
    assert ClientService is not None


def test_client_service_can_be_instantiated():
    """Test that ClientService can be instantiated."""
    service = ClientService(node_url="ws://localhost:8000")
    assert service is not None
    assert service.node_url == "ws://localhost:8000"
    assert not service.is_connected


def test_create_room_request_can_be_created():
    """Test that CreateRoomRequest can be created and serialized."""
    request = CreateRoomRequest(room_name="test", creator_id="user1")
    assert request.room_name == "test"
    assert request.creator_id == "user1"

    # Test serialization
    request_dict = request.to_dict()
    assert request_dict["type"] == "create_room"
    assert request_dict["data"]["room_name"] == "test"
    assert request_dict["data"]["creator_id"] == "user1"

    # Test JSON serialization
    request_json = request.to_json()
    assert "create_room" in request_json
    assert "test" in request_json
    assert "user1" in request_json


def test_room_created_response_can_be_created():
    """Test that RoomCreatedResponse can be created."""
    response = RoomCreatedResponse(
        room_id="room123",
        room_name="test",
        node_id="node1",
        success=True,
        message="Created",
    )
    assert response.room_id == "room123"
    assert response.room_name == "test"
    assert response.node_id == "node1"
    assert response.success is True
    assert response.message == "Created"


def test_room_created_response_from_dict():
    """Test RoomCreatedResponse can be created from dict."""
    data = {
        "data": {
            "room_id": "room123",
            "room_name": "test",
            "node_id": "node1",
            "success": True,
        }
    }
    response = RoomCreatedResponse.from_dict(data)
    assert response.room_id == "room123"
    assert response.room_name == "test"
    assert response.node_id == "node1"
    assert response.success is True


@pytest.mark.asyncio
async def test_client_service_create_room_with_mock():
    """Test that create_room works with mock WebSocket."""
    import json

    # Create a mock websocket
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            # Return a mock response
            return json.dumps(
                {
                    "type": "room_created",
                    "data": {
                        "room_id": "test_room_id",
                        "room_name": "test_room",
                        "node_id": "test_node",
                        "success": True,
                        "message": "Room created successfully",
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocket()
    service._set_test_mode(mock_websocket=mock_ws)

    # Call create_room with mock WebSocket
    response = await service.create_room(
        room_name="test_room", creator_id="test_user"
    )

    # Verify response
    assert response is not None
    assert response.success is True
    assert response.room_name == "test_room"
    assert response.room_id == "test_room_id"

    # Verify request was sent
    assert len(mock_ws.sent_messages) == 1
    sent_msg = json.loads(mock_ws.sent_messages[0])
    assert sent_msg["type"] == "create_room"
    assert sent_msg["data"]["room_name"] == "test_room"
    assert sent_msg["data"]["creator_id"] == "test_user"


def test_list_rooms_request_can_be_created():
    """Test that ListRoomsRequest can be created and serialized."""
    from src.client import ListRoomsRequest

    request = ListRoomsRequest()

    # Test serialization
    request_dict = request.to_dict()
    assert request_dict["type"] == "list_rooms"

    # Test JSON serialization
    request_json = request.to_json()
    assert "list_rooms" in request_json


def test_room_info_can_be_created():
    """Test that RoomInfo can be created."""
    from src.client import RoomInfo

    room = RoomInfo(
        room_id="room123",
        room_name="Test Room",
        description="A test room",
        member_count=5,
        admin_node="node1",
    )
    assert room.room_id == "room123"
    assert room.room_name == "Test Room"
    assert room.description == "A test room"
    assert room.member_count == 5
    assert room.admin_node == "node1"


def test_rooms_list_response_empty_list():
    """Test RoomsListResponse with empty room list."""
    from src.client import RoomsListResponse

    data = {
        "type": "rooms_list",
        "data": {
            "rooms": [],
            "total_count": 0,
        },
    }

    response = RoomsListResponse.from_dict(data)
    assert response.rooms == []
    assert response.total_count == 0


def test_rooms_list_response_with_rooms():
    """Test RoomsListResponse with multiple rooms."""
    from src.client import RoomsListResponse

    data = {
        "type": "rooms_list",
        "data": {
            "rooms": [
                {
                    "room_id": "room-uuid-1",
                    "room_name": "General Chat",
                    "description": "A place for general discussion",
                    "member_count": 5,
                    "admin_node": "node1",
                },
                {
                    "room_id": "room-uuid-2",
                    "room_name": "Tech Talk",
                    "description": "Discuss technology topics",
                    "member_count": 3,
                    "admin_node": "node1",
                },
            ],
            "total_count": 2,
        },
    }

    response = RoomsListResponse.from_dict(data)
    assert len(response.rooms) == 2
    assert response.total_count == 2

    # Check first room
    room1 = response.rooms[0]
    assert room1.room_id == "room-uuid-1"
    assert room1.room_name == "General Chat"
    assert room1.description == "A place for general discussion"
    assert room1.member_count == 5
    assert room1.admin_node == "node1"

    # Check second room
    room2 = response.rooms[1]
    assert room2.room_id == "room-uuid-2"
    assert room2.room_name == "Tech Talk"
    assert room2.description == "Discuss technology topics"
    assert room2.member_count == 3
    assert room2.admin_node == "node1"


def test_rooms_list_response_from_json():
    """Test RoomsListResponse can be created from JSON string."""
    from src.client import RoomsListResponse
    import json

    data = {
        "type": "rooms_list",
        "data": {
            "rooms": [
                {
                    "room_id": "room123",
                    "room_name": "Test Room",
                    "description": None,
                    "member_count": 1,
                    "admin_node": "node1",
                }
            ],
            "total_count": 1,
        },
    }

    json_str = json.dumps(data)
    response = RoomsListResponse.from_json(json_str)

    assert len(response.rooms) == 1
    assert response.total_count == 1
    assert response.rooms[0].room_id == "room123"


@pytest.mark.asyncio
async def test_client_service_list_rooms_not_connected():
    """Test that list_rooms raises error when not connected."""
    service = ClientService(node_url="ws://localhost:8000")

    # Should raise ConnectionError when not connected
    with pytest.raises(ConnectionError, match="Not connected"):
        await service.list_rooms()


@pytest.mark.asyncio
async def test_client_service_list_rooms_with_mock():
    """Test that list_rooms works with mock WebSocket."""
    import json

    # Create a mock websocket
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            # Return a mock response with empty room list
            return json.dumps(
                {
                    "type": "rooms_list",
                    "data": {
                        "rooms": [],
                        "total_count": 0,
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocket()
    service._set_test_mode(mock_websocket=mock_ws)

    # Call list_rooms with mock WebSocket
    response = await service.list_rooms()

    # Verify response returns empty list
    assert response is not None
    assert response.rooms == []
    assert response.total_count == 0

    # Verify request was sent
    assert len(mock_ws.sent_messages) == 1
    sent_msg = json.loads(mock_ws.sent_messages[0])
    assert sent_msg["type"] == "list_rooms"


# TODO: Add tests for:
# - Real WebSocket connection (integration test)
# - Message handler registration
# - Error handling (connection failures, invalid messages, etc.)
# - Disconnect behavior
# - Multiple concurrent operations
