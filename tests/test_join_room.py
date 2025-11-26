"""
Tests for Join Room Functionality

Tests for the join room feature including:
- Protocol messages (JoinRoomRequest, JoinRoomSuccessResponse, etc.)
- WebSocket server handling of join_room messages
- XML-RPC join_room method for cross-node joins
- Client service join_room method
"""

import json
import pytest

from src.client import (
    ClientService,
    JoinRoomRequest,
    JoinRoomSuccessResponse,
    JoinRoomErrorResponse,
    MemberJoinedNotification,
)
from src.node import RoomStateManager, WebSocketServer, XMLRPCServer


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


# Protocol Message Tests


def test_join_room_request_can_be_created():
    """Test that JoinRoomRequest can be created and serialized."""
    request = JoinRoomRequest(room_id="room-123", username="alice")
    assert request.room_id == "room-123"
    assert request.username == "alice"

    # Test serialization
    request_dict = request.to_dict()
    assert request_dict["type"] == "join_room"
    assert request_dict["data"]["room_id"] == "room-123"
    assert request_dict["data"]["username"] == "alice"

    # Test JSON serialization
    request_json = request.to_json()
    assert "join_room" in request_json
    assert "room-123" in request_json
    assert "alice" in request_json


def test_join_room_success_response_can_be_created():
    """Test that JoinRoomSuccessResponse can be created."""
    response = JoinRoomSuccessResponse(
        room_id="room-123",
        room_name="General Chat",
        description="A place for general discussion",
        members=["bob", "carol", "alice"],
        member_count=3,
        admin_node="node1",
    )
    assert response.room_id == "room-123"
    assert response.room_name == "General Chat"
    assert response.description == "A place for general discussion"
    assert response.members == ["bob", "carol", "alice"]
    assert response.member_count == 3
    assert response.admin_node == "node1"


def test_join_room_success_response_from_dict():
    """Test JoinRoomSuccessResponse can be created from dict."""
    data = {
        "type": "join_room_success",
        "data": {
            "room_id": "room-123",
            "room_name": "General Chat",
            "description": "A place for general discussion",
            "members": ["bob", "carol", "alice"],
            "member_count": 3,
            "admin_node": "node1",
        },
    }
    response = JoinRoomSuccessResponse.from_dict(data)
    assert response.room_id == "room-123"
    assert response.room_name == "General Chat"
    assert response.members == ["bob", "carol", "alice"]


def test_join_room_success_response_from_json():
    """Test JoinRoomSuccessResponse can be created from JSON."""
    json_str = json.dumps(
        {
            "type": "join_room_success",
            "data": {
                "room_id": "room-123",
                "room_name": "Test Room",
                "description": None,
                "members": ["alice"],
                "member_count": 1,
                "admin_node": "node1",
            },
        }
    )
    response = JoinRoomSuccessResponse.from_json(json_str)
    assert response.room_id == "room-123"
    assert response.room_name == "Test Room"


def test_join_room_error_response_can_be_created():
    """Test that JoinRoomErrorResponse can be created."""
    response = JoinRoomErrorResponse(
        room_id="room-123",
        error="Room not found",
        error_code="ROOM_NOT_FOUND",
    )
    assert response.room_id == "room-123"
    assert response.error == "Room not found"
    assert response.error_code == "ROOM_NOT_FOUND"


def test_join_room_error_response_from_dict():
    """Test JoinRoomErrorResponse can be created from dict."""
    data = {
        "type": "join_room_error",
        "data": {
            "room_id": "room-123",
            "error": "Already in room",
            "error_code": "ALREADY_IN_ROOM",
        },
    }
    response = JoinRoomErrorResponse.from_dict(data)
    assert response.room_id == "room-123"
    assert response.error == "Already in room"
    assert response.error_code == "ALREADY_IN_ROOM"


def test_member_joined_notification_can_be_created():
    """Test that MemberJoinedNotification can be created."""
    notification = MemberJoinedNotification(
        room_id="room-123",
        username="alice",
        member_count=3,
        timestamp="2025-11-23T10:30:00Z",
    )
    assert notification.room_id == "room-123"
    assert notification.username == "alice"
    assert notification.member_count == 3
    assert notification.timestamp == "2025-11-23T10:30:00Z"


def test_member_joined_notification_from_dict():
    """Test MemberJoinedNotification can be created from dict."""
    data = {
        "type": "member_joined",
        "data": {
            "room_id": "room-123",
            "username": "alice",
            "member_count": 3,
            "timestamp": "2025-11-23T10:30:00Z",
        },
    }
    notification = MemberJoinedNotification.from_dict(data)
    assert notification.room_id == "room-123"
    assert notification.username == "alice"


# WebSocket Server Tests


@pytest.mark.asyncio
async def test_websocket_join_room_success():
    """Test join_room WebSocket message handling for local room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room first
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator", description="A test room"
    )

    mock_ws = MockWebSocket()

    # Create join_room request
    request = json.dumps(
        {
            "type": "join_room",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    # Verify response was sent
    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "join_room_success"
    assert response["data"]["room_id"] == room.room_id
    assert response["data"]["room_name"] == "Test Room"
    assert "alice" in response["data"]["members"]
    assert response["data"]["member_count"] == 1  # just alice (room starts empty)


@pytest.mark.asyncio
async def test_websocket_join_room_not_found():
    """Test join_room with non-existent room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "join_room",
            "data": {
                "room_id": "non-existent-room",
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "join_room_error"
    assert response["data"]["error_code"] == "ROOM_NOT_FOUND"


@pytest.mark.asyncio
async def test_websocket_join_room_already_in_room():
    """Test join_room when user is already in the room allows re-joining."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room and add alice
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "join_room",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    # Users who are already members can re-join (e.g., room creator)
    # This allows their WebSocket connection to be registered
    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "join_room_success"
    assert response["data"]["room_id"] == room.room_id


@pytest.mark.asyncio
async def test_websocket_join_room_missing_fields():
    """Test join_room with missing required fields."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()

    # Missing username
    request = json.dumps(
        {
            "type": "join_room",
            "data": {
                "room_id": "room-123",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "join_room_error"
    assert response["data"]["error_code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_websocket_join_room_broadcast_to_members():
    """Test that member_joined is broadcast to existing members."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    # Add an existing member with their websocket
    existing_ws = MockWebSocket()
    ws_server.register_client_room_membership(
        existing_ws, room.room_id, "creator"
    )

    # New user joins
    joining_ws = MockWebSocket()
    request = json.dumps(
        {
            "type": "join_room",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(joining_ws, request)

    # Joining user should get success response
    assert len(joining_ws.sent_messages) == 1
    response = json.loads(joining_ws.sent_messages[0])
    assert response["type"] == "join_room_success"

    # Existing member should get member_joined notification
    assert len(existing_ws.sent_messages) == 1
    notification = json.loads(existing_ws.sent_messages[0])
    assert notification["type"] == "member_joined"
    assert notification["data"]["username"] == "alice"
    assert notification["data"]["room_id"] == room.room_id


# XML-RPC Server Tests


def test_xmlrpc_join_room_success():
    """Test XML-RPC join_room method for successful join."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    # Create a room
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator", description="A test room"
    )

    # Call join_room via XML-RPC
    result = server.join_room(room.room_id, "alice", "client_node")

    assert result["success"] is True
    assert result["room_info"]["room_id"] == room.room_id
    assert result["room_info"]["room_name"] == "Test Room"
    assert "alice" in result["room_info"]["members"]


def test_xmlrpc_join_room_not_found():
    """Test XML-RPC join_room method with non-existent room."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    result = server.join_room("non-existent-room", "alice", "client_node")

    assert result["success"] is False
    assert result["error_code"] == "ROOM_NOT_FOUND"
    assert result["room_info"] is None


def test_xmlrpc_join_room_already_in_room():
    """Test XML-RPC join_room method when user is already in room."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    # Create a room and add alice
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    result = server.join_room(room.room_id, "alice", "client_node")

    assert result["success"] is False
    assert result["error_code"] == "ALREADY_IN_ROOM"


# Client Service Tests


@pytest.mark.asyncio
async def test_client_service_join_room_not_connected():
    """Test that join_room raises error when not connected."""
    service = ClientService(node_url="ws://localhost:8000")

    with pytest.raises(ConnectionError, match="Not connected"):
        await service.join_room("room-123", "alice")


@pytest.mark.asyncio
async def test_client_service_join_room_success():
    """Test that join_room works with mock WebSocket."""

    class MockWebSocketClient:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            return json.dumps(
                {
                    "type": "join_room_success",
                    "data": {
                        "room_id": "room-123",
                        "room_name": "Test Room",
                        "description": "A test room",
                        "members": ["alice"],
                        "member_count": 1,
                        "admin_node": "node1",
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocketClient()
    service._set_test_mode(mock_websocket=mock_ws)

    response = await service.join_room("room-123", "alice")

    assert response.room_id == "room-123"
    assert response.room_name == "Test Room"
    assert response.members == ["alice"]

    # Verify request was sent
    assert len(mock_ws.sent_messages) == 1
    sent_msg = json.loads(mock_ws.sent_messages[0])
    assert sent_msg["type"] == "join_room"
    assert sent_msg["data"]["room_id"] == "room-123"
    assert sent_msg["data"]["username"] == "alice"


@pytest.mark.asyncio
async def test_client_service_join_room_error():
    """Test that join_room raises ValueError on error response."""

    class MockWebSocketClient:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            return json.dumps(
                {
                    "type": "join_room_error",
                    "data": {
                        "room_id": "room-123",
                        "error": "Room not found",
                        "error_code": "ROOM_NOT_FOUND",
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocketClient()
    service._set_test_mode(mock_websocket=mock_ws)

    with pytest.raises(ValueError, match="Room not found"):
        await service.join_room("room-123", "alice")


# Client Room Membership Tracking Tests


def test_register_client_room_membership():
    """Test registering client room membership."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(mock_ws, "room-123", "alice")

    assert "room-123" in ws_server._room_clients
    assert (mock_ws, "alice") in ws_server._room_clients["room-123"]
    assert mock_ws in ws_server._client_rooms
    assert "room-123" in ws_server._client_rooms[mock_ws]


def test_unregister_client_room_membership_specific_room():
    """Test unregistering client from a specific room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(mock_ws, "room-123", "alice")
    ws_server.register_client_room_membership(mock_ws, "room-456", "alice")

    ws_server.unregister_client_room_membership(mock_ws, "room-123")

    # Should still be in room-456
    assert (mock_ws, "alice") not in ws_server._room_clients.get(
        "room-123", set()
    )
    assert "room-456" in ws_server._client_rooms[mock_ws]


def test_unregister_client_room_membership_all_rooms():
    """Test unregistering client from all rooms."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(mock_ws, "room-123", "alice")
    ws_server.register_client_room_membership(mock_ws, "room-456", "alice")

    ws_server.unregister_client_room_membership(mock_ws)

    # Should be removed from all rooms
    assert (mock_ws, "alice") not in ws_server._room_clients.get(
        "room-123", set()
    )
    assert (mock_ws, "alice") not in ws_server._room_clients.get(
        "room-456", set()
    )
    assert mock_ws not in ws_server._client_rooms
