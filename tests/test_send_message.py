"""
Tests for Send Message Functionality

Tests for the send message feature including:
- Protocol messages (SendMessageRequest, MessageSentConfirmation, etc.)
- WebSocket server handling of send_message messages
- XML-RPC forward_message and receive_message_broadcast methods
- Client service send_message method
- Room message counter and message buffer
"""

import json
import pytest

from src.client import (
    ClientService,
    SendMessageRequest,
    MessageSentConfirmation,
    NewMessageNotification,
    MessageErrorResponse,
)
from src.node import RoomStateManager, WebSocketServer, XMLRPCServer


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


# Protocol Message Tests


def test_send_message_request_can_be_created():
    """Test that SendMessageRequest can be created and serialized."""
    request = SendMessageRequest(
        room_id="room-123", username="alice", content="Hello everyone!"
    )
    assert request.room_id == "room-123"
    assert request.username == "alice"
    assert request.content == "Hello everyone!"

    # Test serialization
    request_dict = request.to_dict()
    assert request_dict["type"] == "send_message"
    assert request_dict["data"]["room_id"] == "room-123"
    assert request_dict["data"]["username"] == "alice"
    assert request_dict["data"]["content"] == "Hello everyone!"

    # Test JSON serialization
    request_json = request.to_json()
    assert "send_message" in request_json
    assert "room-123" in request_json
    assert "Hello everyone!" in request_json


def test_message_sent_confirmation_can_be_created():
    """Test that MessageSentConfirmation can be created."""
    confirmation = MessageSentConfirmation(
        room_id="room-123",
        message_id="msg-456",
        sequence_number=42,
        timestamp="2025-11-23T10:30:15Z",
    )
    assert confirmation.room_id == "room-123"
    assert confirmation.message_id == "msg-456"
    assert confirmation.sequence_number == 42
    assert confirmation.timestamp == "2025-11-23T10:30:15Z"


def test_message_sent_confirmation_from_dict():
    """Test MessageSentConfirmation can be created from dict."""
    data = {
        "type": "message_sent",
        "data": {
            "room_id": "room-123",
            "message_id": "msg-456",
            "sequence_number": 42,
            "timestamp": "2025-11-23T10:30:15Z",
        },
    }
    confirmation = MessageSentConfirmation.from_dict(data)
    assert confirmation.room_id == "room-123"
    assert confirmation.message_id == "msg-456"
    assert confirmation.sequence_number == 42


def test_message_sent_confirmation_from_json():
    """Test MessageSentConfirmation can be created from JSON."""
    json_str = json.dumps(
        {
            "type": "message_sent",
            "data": {
                "room_id": "room-123",
                "message_id": "msg-456",
                "sequence_number": 1,
                "timestamp": "2025-11-23T10:30:15Z",
            },
        }
    )
    confirmation = MessageSentConfirmation.from_json(json_str)
    assert confirmation.room_id == "room-123"
    assert confirmation.sequence_number == 1


def test_new_message_notification_can_be_created():
    """Test that NewMessageNotification can be created."""
    notification = NewMessageNotification(
        room_id="room-123",
        message_id="msg-456",
        username="alice",
        content="Hello!",
        sequence_number=42,
        timestamp="2025-11-23T10:30:15Z",
    )
    assert notification.room_id == "room-123"
    assert notification.message_id == "msg-456"
    assert notification.username == "alice"
    assert notification.content == "Hello!"
    assert notification.sequence_number == 42


def test_new_message_notification_from_dict():
    """Test NewMessageNotification can be created from dict."""
    data = {
        "type": "new_message",
        "data": {
            "room_id": "room-123",
            "message_id": "msg-456",
            "username": "alice",
            "content": "Hello!",
            "sequence_number": 42,
            "timestamp": "2025-11-23T10:30:15Z",
        },
    }
    notification = NewMessageNotification.from_dict(data)
    assert notification.room_id == "room-123"
    assert notification.username == "alice"
    assert notification.content == "Hello!"


def test_message_error_response_can_be_created():
    """Test that MessageErrorResponse can be created."""
    response = MessageErrorResponse(
        room_id="room-123",
        error="You are not a member of this room",
        error_code="NOT_MEMBER",
    )
    assert response.room_id == "room-123"
    assert response.error == "You are not a member of this room"
    assert response.error_code == "NOT_MEMBER"


def test_message_error_response_from_dict():
    """Test MessageErrorResponse can be created from dict."""
    data = {
        "type": "message_error",
        "data": {
            "room_id": "room-123",
            "error": "Message content too long",
            "error_code": "INVALID_CONTENT",
        },
    }
    response = MessageErrorResponse.from_dict(data)
    assert response.room_id == "room-123"
    assert response.error == "Message content too long"
    assert response.error_code == "INVALID_CONTENT"


# RoomStateManager Message Tests


def test_room_has_message_counter():
    """Test that rooms have a message counter."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    assert room.message_counter == 0
    assert room.messages == []


def test_add_message_to_room():
    """Test adding a message to a room."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    # Add a message
    message = manager.add_message(
        room.room_id, "creator", "Hello world!"
    )

    assert message is not None
    assert message["username"] == "creator"
    assert message["content"] == "Hello world!"
    assert message["sequence_number"] == 1
    assert "message_id" in message
    assert "timestamp" in message
    assert room.message_counter == 1
    assert len(room.messages) == 1


def test_add_multiple_messages_increments_sequence():
    """Test that sequence numbers increment."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    msg1 = manager.add_message(room.room_id, "creator", "First")
    msg2 = manager.add_message(room.room_id, "creator", "Second")
    msg3 = manager.add_message(room.room_id, "creator", "Third")

    assert msg1["sequence_number"] == 1
    assert msg2["sequence_number"] == 2
    assert msg3["sequence_number"] == 3
    assert room.message_counter == 3


def test_add_message_non_member_fails():
    """Test that non-members cannot add messages."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    # Try to add message as non-member
    message = manager.add_message(room.room_id, "stranger", "Hello!")

    assert message is None
    assert room.message_counter == 0


def test_add_message_nonexistent_room_fails():
    """Test that adding to nonexistent room fails."""
    manager = RoomStateManager(node_id="test_node")

    message = manager.add_message("fake-room", "user", "Hello!")

    assert message is None


def test_message_buffer_limit():
    """Test that message buffer respects size limit."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    # Add more messages than the limit
    for i in range(105):
        manager.add_message(
            room.room_id, "creator", f"Message {i}", max_messages=100
        )

    # Buffer should be limited
    assert len(room.messages) == 100
    # Oldest messages should be removed
    assert room.messages[0]["content"] == "Message 5"
    assert room.messages[-1]["content"] == "Message 104"


# WebSocket Server Tests


@pytest.mark.asyncio
async def test_websocket_send_message_success():
    """Test send_message WebSocket message handling for local room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room and add the user
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    mock_ws = MockWebSocket()

    # Register alice as a room member
    ws_server.register_client_room_membership(
        mock_ws, room.room_id, "alice"
    )

    # Create send_message request
    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
                "content": "Hello everyone!",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    # Should get both new_message broadcast and message_sent confirmation
    assert len(mock_ws.sent_messages) == 2

    # Check for new_message broadcast
    messages_types = [
        json.loads(msg)["type"] for msg in mock_ws.sent_messages
    ]
    assert "new_message" in messages_types
    assert "message_sent" in messages_types

    # Check message_sent confirmation
    for msg in mock_ws.sent_messages:
        parsed = json.loads(msg)
        if parsed["type"] == "message_sent":
            assert parsed["data"]["room_id"] == room.room_id
            assert parsed["data"]["sequence_number"] == 1
            assert "message_id" in parsed["data"]
            assert "timestamp" in parsed["data"]


@pytest.mark.asyncio
async def test_websocket_send_message_not_member():
    """Test send_message when user is not a member of the room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room (alice is not a member)
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    mock_ws = MockWebSocket()

    # Don't register alice as a room member

    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
                "content": "Hello!",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "message_error"
    assert response["data"]["error_code"] == "NOT_MEMBER"


@pytest.mark.asyncio
async def test_websocket_send_message_empty_content():
    """Test send_message with empty content."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(
        mock_ws, room.room_id, "alice"
    )

    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
                "content": "",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "message_error"
    assert response["data"]["error_code"] == "INVALID_CONTENT"


@pytest.mark.asyncio
async def test_websocket_send_message_too_long():
    """Test send_message with content exceeding max length."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(
        mock_ws, room.room_id, "alice"
    )

    # Content exceeding 5000 characters
    long_content = "x" * 5001

    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
                "content": long_content,
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "message_error"
    assert response["data"]["error_code"] == "INVALID_CONTENT"


@pytest.mark.asyncio
async def test_websocket_send_message_missing_fields():
    """Test send_message with missing required fields."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()

    # Missing username
    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": "room-123",
                "content": "Hello!",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1

    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "message_error"
    assert response["data"]["error_code"] == "INVALID_REQUEST"


@pytest.mark.asyncio
async def test_websocket_send_message_broadcast_to_room_members():
    """Test that new_message is broadcast to all room members."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")
    room_manager.add_member(room.room_id, "bob")

    # Set up websockets for all members
    creator_ws = MockWebSocket()
    alice_ws = MockWebSocket()
    bob_ws = MockWebSocket()

    ws_server.register_client_room_membership(
        creator_ws, room.room_id, "creator"
    )
    ws_server.register_client_room_membership(
        alice_ws, room.room_id, "alice"
    )
    ws_server.register_client_room_membership(
        bob_ws, room.room_id, "bob"
    )

    # Alice sends a message
    request = json.dumps(
        {
            "type": "send_message",
            "data": {
                "room_id": room.room_id,
                "username": "alice",
                "content": "Hello everyone!",
            },
        }
    )

    await ws_server.process_message(alice_ws, request)

    # All members should receive the new_message broadcast
    for ws in [creator_ws, alice_ws, bob_ws]:
        new_message_found = False
        for msg in ws.sent_messages:
            parsed = json.loads(msg)
            if parsed["type"] == "new_message":
                new_message_found = True
                assert parsed["data"]["username"] == "alice"
                assert parsed["data"]["content"] == "Hello everyone!"
                assert parsed["data"]["sequence_number"] == 1
        assert new_message_found, f"new_message not found for websocket"


# XML-RPC Server Tests


def test_xmlrpc_forward_message_success():
    """Test XML-RPC forward_message method for successful message."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    # Create a room and add member
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )
    room_manager.add_member(room.room_id, "alice")

    # Forward a message
    result = server.forward_message(
        room.room_id, "alice", "Hello!", "client_node"
    )

    assert result["success"] is True
    assert "message_id" in result
    assert result["sequence_number"] == 1
    assert "timestamp" in result


def test_xmlrpc_forward_message_not_member():
    """Test XML-RPC forward_message when user is not a member."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    result = server.forward_message(
        room.room_id, "stranger", "Hello!", "client_node"
    )

    assert result["success"] is False
    assert result["error_code"] == "NOT_MEMBER"


def test_xmlrpc_forward_message_room_not_found():
    """Test XML-RPC forward_message with non-existent room."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    result = server.forward_message(
        "non-existent-room", "alice", "Hello!", "client_node"
    )

    assert result["success"] is False
    assert result["error_code"] == "ROOM_NOT_FOUND"


def test_xmlrpc_forward_message_empty_content():
    """Test XML-RPC forward_message with empty content."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    result = server.forward_message(
        room.room_id, "creator", "", "client_node"
    )

    assert result["success"] is False
    assert result["error_code"] == "INVALID_CONTENT"


def test_xmlrpc_forward_message_too_long():
    """Test XML-RPC forward_message with content too long."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator"
    )

    long_content = "x" * 5001

    result = server.forward_message(
        room.room_id, "creator", long_content, "client_node"
    )

    assert result["success"] is False
    assert result["error_code"] == "INVALID_CONTENT"


def test_xmlrpc_receive_message_broadcast():
    """Test XML-RPC receive_message_broadcast method."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    received_broadcasts = []

    def mock_callback(room_id, message, exclude_user=None):
        received_broadcasts.append((room_id, message))

    server.set_broadcast_callback(mock_callback)

    message_data = {
        "message_id": "msg-123",
        "username": "alice",
        "content": "Hello!",
        "sequence_number": 42,
        "timestamp": "2025-11-23T10:30:15Z",
    }

    result = server.receive_message_broadcast("room-123", message_data)

    assert result is True
    assert len(received_broadcasts) == 1
    assert received_broadcasts[0][0] == "room-123"
    assert received_broadcasts[0][1]["type"] == "new_message"
    assert received_broadcasts[0][1]["data"] == message_data


# Client Service Tests


@pytest.mark.asyncio
async def test_client_service_send_message_not_connected():
    """Test that send_message raises error when not connected."""
    service = ClientService(node_url="ws://localhost:8000")

    with pytest.raises(ConnectionError, match="Not connected"):
        await service.send_message("room-123", "alice", "Hello!")


@pytest.mark.asyncio
async def test_client_service_send_message_success():
    """Test that send_message works with mock WebSocket."""

    class MockWebSocketClient:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            return json.dumps(
                {
                    "type": "message_sent",
                    "data": {
                        "room_id": "room-123",
                        "message_id": "msg-456",
                        "sequence_number": 42,
                        "timestamp": "2025-11-23T10:30:15Z",
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocketClient()
    service._set_test_mode(mock_websocket=mock_ws)

    response = await service.send_message(
        "room-123", "alice", "Hello everyone!"
    )

    assert response.room_id == "room-123"
    assert response.message_id == "msg-456"
    assert response.sequence_number == 42

    # Verify request was sent
    assert len(mock_ws.sent_messages) == 1
    sent_msg = json.loads(mock_ws.sent_messages[0])
    assert sent_msg["type"] == "send_message"
    assert sent_msg["data"]["room_id"] == "room-123"
    assert sent_msg["data"]["username"] == "alice"
    assert sent_msg["data"]["content"] == "Hello everyone!"


@pytest.mark.asyncio
async def test_client_service_send_message_error():
    """Test that send_message raises ValueError on error response."""

    class MockWebSocketClient:
        def __init__(self):
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        async def recv(self):
            return json.dumps(
                {
                    "type": "message_error",
                    "data": {
                        "room_id": "room-123",
                        "error": "You are not a member of this room",
                        "error_code": "NOT_MEMBER",
                    },
                }
            )

    service = ClientService(node_url="ws://localhost:8000")
    mock_ws = MockWebSocketClient()
    service._set_test_mode(mock_websocket=mock_ws)

    with pytest.raises(ValueError, match="not a member"):
        await service.send_message("room-123", "alice", "Hello!")
