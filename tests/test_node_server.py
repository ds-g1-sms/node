"""
Tests for Node Server

Tests for room state management and WebSocket server functionality.
"""

import pytest
from src.node import RoomStateManager


def test_room_state_manager_can_be_created():
    """Test that RoomStateManager can be created."""
    manager = RoomStateManager(node_id="test_node")
    assert manager is not None
    assert manager.node_id == "test_node"
    assert manager.get_room_count() == 0


def test_create_room():
    """Test creating a room."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(
        room_name="Test Room", creator_id="user1", description="A test room"
    )

    assert room is not None
    assert room.room_name == "Test Room"
    assert room.creator_id == "user1"
    assert room.description == "A test room"
    assert room.admin_node == "test_node"
    assert "user1" in room.members
    assert manager.get_room_count() == 1


def test_create_duplicate_room_raises_error():
    """Test that creating a room with duplicate name raises error."""
    manager = RoomStateManager(node_id="test_node")

    # Create first room
    manager.create_room(room_name="Test Room", creator_id="user1")

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        manager.create_room(room_name="Test Room", creator_id="user2")


def test_list_rooms_empty():
    """Test listing rooms when none exist."""
    manager = RoomStateManager(node_id="test_node")

    rooms = manager.list_rooms()
    assert rooms == []


def test_list_rooms_with_rooms():
    """Test listing rooms when they exist."""
    manager = RoomStateManager(node_id="test_node")

    # Create multiple rooms
    room1 = manager.create_room(
        room_name="Room 1", creator_id="user1", description="First room"
    )
    room2 = manager.create_room(
        room_name="Room 2", creator_id="user2", description="Second room"
    )

    rooms = manager.list_rooms()
    assert len(rooms) == 2

    # Check room data structure
    room1_data = next(r for r in rooms if r["room_name"] == "Room 1")
    assert room1_data["room_id"] == room1.room_id
    assert room1_data["room_name"] == "Room 1"
    assert room1_data["description"] == "First room"
    assert room1_data["member_count"] == 1
    assert room1_data["admin_node"] == "test_node"

    room2_data = next(r for r in rooms if r["room_name"] == "Room 2")
    assert room2_data["room_id"] == room2.room_id
    assert room2_data["room_name"] == "Room 2"
    assert room2_data["description"] == "Second room"
    assert room2_data["member_count"] == 1
    assert room2_data["admin_node"] == "test_node"


def test_get_room():
    """Test getting a room by ID."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # Get existing room
    retrieved_room = manager.get_room(room.room_id)
    assert retrieved_room is not None
    assert retrieved_room.room_id == room.room_id
    assert retrieved_room.room_name == "Test Room"

    # Get non-existent room
    non_existent = manager.get_room("invalid_id")
    assert non_existent is None


def test_delete_room():
    """Test deleting a room."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(room_name="Test Room", creator_id="user1")
    assert manager.get_room_count() == 1

    # Delete the room
    result = manager.delete_room(room.room_id)
    assert result is True
    assert manager.get_room_count() == 0

    # Try to delete non-existent room
    result = manager.delete_room("invalid_id")
    assert result is False


def test_add_member():
    """Test adding a member to a room."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(room_name="Test Room", creator_id="user1")
    assert len(room.members) == 1

    # Add a member
    result = manager.add_member(room.room_id, "user2")
    assert result is True
    assert "user2" in room.members
    assert len(room.members) == 2

    # Try to add member to non-existent room
    result = manager.add_member("invalid_id", "user3")
    assert result is False


def test_remove_member():
    """Test removing a member from a room."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(room_name="Test Room", creator_id="user1")
    manager.add_member(room.room_id, "user2")
    assert len(room.members) == 2

    # Remove a member
    result = manager.remove_member(room.room_id, "user2")
    assert result is True
    assert "user2" not in room.members
    assert len(room.members) == 1

    # Try to remove non-existent member
    result = manager.remove_member(room.room_id, "user3")
    assert result is False

    # Try to remove member from non-existent room
    result = manager.remove_member("invalid_id", "user1")
    assert result is False


def test_room_to_dict():
    """Test room serialization to dictionary."""
    manager = RoomStateManager(node_id="test_node")

    room = manager.create_room(
        room_name="Test Room", creator_id="user1", description="A test room"
    )
    manager.add_member(room.room_id, "user2")

    room_dict = room.to_dict()

    assert room_dict["room_id"] == room.room_id
    assert room_dict["room_name"] == "Test Room"
    assert room_dict["description"] == "A test room"
    assert room_dict["member_count"] == 2
    assert room_dict["admin_node"] == "test_node"


@pytest.mark.asyncio
async def test_websocket_create_room_success():
    """Test create_room WebSocket message handling."""
    import json
    from src.node import WebSocketServer

    # Create room manager and WebSocket server
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a mock websocket connection
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

    mock_ws = MockWebSocket()

    # Create request message
    request = json.dumps(
        {
            "type": "create_room",
            "data": {
                "room_name": "Test Room",
                "creator_id": "user123",
                "description": "A test room",
            },
        }
    )

    # Process the message
    await ws_server.process_message(mock_ws, request)

    # Verify response was sent
    assert len(mock_ws.sent_messages) == 1

    # Parse response
    response = json.loads(mock_ws.sent_messages[0])

    # Verify response structure
    assert response["type"] == "room_created"
    assert "data" in response

    data = response["data"]
    assert "room_id" in data
    assert data["room_name"] == "Test Room"
    assert data["admin_node"] == "test_node"
    assert data["members"] == ["user123"]
    assert "created_at" in data

    # Verify room was actually created
    assert room_manager.get_room_count() == 1


@pytest.mark.asyncio
async def test_websocket_create_room_duplicate_name():
    """Test create_room with duplicate room name."""
    import json
    from src.node import WebSocketServer

    # Create room manager and WebSocket server
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a mock websocket connection
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

    mock_ws = MockWebSocket()

    # Create first room
    request1 = json.dumps(
        {
            "type": "create_room",
            "data": {
                "room_name": "Test Room",
                "creator_id": "user1",
            },
        }
    )
    await ws_server.process_message(mock_ws, request1)

    # Try to create duplicate room
    request2 = json.dumps(
        {
            "type": "create_room",
            "data": {
                "room_name": "Test Room",
                "creator_id": "user2",
            },
        }
    )
    await ws_server.process_message(mock_ws, request2)

    # Should have two responses
    assert len(mock_ws.sent_messages) == 2

    # First should succeed
    response1 = json.loads(mock_ws.sent_messages[0])
    assert response1["type"] == "room_created"

    # Second should be error
    response2 = json.loads(mock_ws.sent_messages[1])
    assert response2["type"] == "room_created"
    assert response2["data"]["success"] is False
    assert "already exists" in response2["data"]["message"]

    # Only one room should be created
    assert room_manager.get_room_count() == 1


@pytest.mark.asyncio
async def test_websocket_create_room_missing_fields():
    """Test create_room with missing required fields."""
    import json
    from src.node import WebSocketServer

    # Create room manager and WebSocket server
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a mock websocket connection
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

    mock_ws = MockWebSocket()

    # Create request missing creator_id
    request = json.dumps(
        {
            "type": "create_room",
            "data": {
                "room_name": "Test Room",
            },
        }
    )

    # Process the message
    await ws_server.process_message(mock_ws, request)

    # Verify error response was sent
    assert len(mock_ws.sent_messages) == 1

    # Parse response
    response = json.loads(mock_ws.sent_messages[0])

    # Verify error response
    assert response["type"] == "room_created"
    assert response["data"]["success"] is False
    assert "creator_id" in response["data"]["message"]


@pytest.mark.asyncio
async def test_websocket_create_room_with_optional_description():
    """Test create_room with optional description."""
    import json
    from src.node import WebSocketServer

    # Create room manager and WebSocket server
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a mock websocket connection
    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

    mock_ws = MockWebSocket()

    # Create request without description
    request = json.dumps(
        {
            "type": "create_room",
            "data": {
                "room_name": "Test Room",
                "creator_id": "user123",
            },
        }
    )

    # Process the message
    await ws_server.process_message(mock_ws, request)

    # Verify response was sent
    assert len(mock_ws.sent_messages) == 1

    # Parse response
    response = json.loads(mock_ws.sent_messages[0])

    # Verify success
    assert response["type"] == "room_created"
    assert response["data"]["room_name"] == "Test Room"

    # Verify room was created without description
    room = room_manager.get_room(response["data"]["room_id"])
    assert room is not None
    assert room.description is None


# TODO: Add more WebSocket server tests
# - Test list_rooms WebSocket message handling
# - Test error handling for invalid JSON
# - Test multiple concurrent client connections
