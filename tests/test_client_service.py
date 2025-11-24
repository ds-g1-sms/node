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
async def test_client_service_stub_create_room():
    """Test that create_room stub works with mock connection."""
    service = ClientService(node_url="ws://localhost:8000")

    # Manually mark as connected for testing
    service._connected = True
    service.websocket = object()

    # Call create_room with stub implementation
    response = await service.create_room(
        room_name="test_room", creator_id="test_user"
    )

    # Verify stub response
    assert response is not None
    assert response.success is True
    assert response.room_name == "test_room"
    assert "stub" in response.message.lower()


# TODO: Add tests for:
# - Real WebSocket connection (integration test)
# - Message handler registration
# - Error handling (connection failures, invalid messages, etc.)
# - Disconnect behavior
# - Multiple concurrent operations
