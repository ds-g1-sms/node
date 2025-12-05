"""
Tests for Member Disconnect Detection

Tests for the disconnect detection functionality including:
- WebSocket disconnect handling
- XML-RPC notify_member_disconnect method
- Node health tracking
- Stale member detection
"""

import json
import pytest
from datetime import datetime, timezone, timedelta

from src.node import (
    RoomStateManager,
    WebSocketServer,
    XMLRPCServer,
    MemberInfo,
    NodeHealth,
    NodeStatus,
    INACTIVITY_TIMEOUT,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []
        self.closed = False

    async def send(self, message):
        self.sent_messages.append(message)


# MemberInfo Tests


def test_member_info_can_be_created():
    """Test that MemberInfo can be created with defaults."""
    info = MemberInfo(username="alice", node_id="node1")
    assert info.username == "alice"
    assert info.node_id == "node1"
    assert info.joined_at != ""
    assert info.last_activity != ""


def test_member_info_update_activity():
    """Test that update_activity updates the timestamp."""
    info = MemberInfo(username="alice", node_id="node1")
    old_activity = info.last_activity

    # Wait a tiny bit to ensure timestamp changes
    import time

    time.sleep(0.01)

    info.update_activity()
    assert info.last_activity != old_activity


def test_member_info_to_dict():
    """Test MemberInfo serialization."""
    info = MemberInfo(username="alice", node_id="node1")
    data = info.to_dict()

    assert data["username"] == "alice"
    assert data["node_id"] == "node1"
    assert "joined_at" in data
    assert "last_activity" in data


# NodeHealth Tests


def test_node_health_can_be_created():
    """Test that NodeHealth can be created."""
    health = NodeHealth(node_id="node1")
    assert health.node_id == "node1"
    assert health.status == NodeStatus.HEALTHY
    assert health.consecutive_failures == 0


def test_node_health_record_success():
    """Test recording a successful heartbeat."""
    health = NodeHealth(node_id="node1")
    health.consecutive_failures = 1
    health.status = NodeStatus.DEGRADED

    health.record_success()

    assert health.status == NodeStatus.HEALTHY
    assert health.consecutive_failures == 0


def test_node_health_record_failure_degrades():
    """Test that a single failure degrades status."""
    health = NodeHealth(node_id="node1")

    is_failed = health.record_failure()

    assert is_failed is False
    assert health.status == NodeStatus.DEGRADED
    assert health.consecutive_failures == 1


def test_node_health_record_failure_marks_failed():
    """Test that multiple failures mark node as failed."""
    health = NodeHealth(node_id="node1")

    # First failure
    is_failed = health.record_failure()
    assert is_failed is False
    assert health.status == NodeStatus.DEGRADED

    # Second failure (reaches MAX_HEARTBEAT_FAILURES=2)
    is_failed = health.record_failure()
    assert is_failed is True
    assert health.status == NodeStatus.FAILED


def test_node_health_to_dict():
    """Test NodeHealth serialization."""
    health = NodeHealth(node_id="node1")
    data = health.to_dict()

    assert data["node_id"] == "node1"
    assert data["status"] == "healthy"
    assert data["consecutive_failures"] == 0


# RoomStateManager Member Tracking Tests


def test_add_member_with_node_id():
    """Test adding a member with node ID tracking."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")

    manager.add_member(room.room_id, "alice", "node2")

    assert "alice" in room.members
    assert "alice" in room.member_info
    assert room.member_info["alice"].node_id == "node2"


def test_add_member_defaults_to_local_node():
    """Test that add_member defaults to local node."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")

    manager.add_member(room.room_id, "alice")

    assert room.member_info["alice"].node_id == "test_node"


def test_remove_member_clears_member_info():
    """Test that remove_member clears member_info."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")
    manager.add_member(room.room_id, "alice", "node2")

    manager.remove_member(room.room_id, "alice")

    assert "alice" not in room.members
    assert "alice" not in room.member_info


def test_get_members_by_node():
    """Test getting members by node ID."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")

    manager.add_member(room.room_id, "alice", "node2")
    manager.add_member(room.room_id, "bob", "node2")
    manager.add_member(room.room_id, "carol", "node3")

    node2_members = manager.get_members_by_node(room.room_id, "node2")

    assert len(node2_members) == 2
    assert "alice" in node2_members
    assert "bob" in node2_members


def test_get_stale_members_empty_when_all_active():
    """Test that no members are stale when all are active."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")
    manager.add_member(room.room_id, "alice", "node2")

    stale = manager.get_stale_members(room.room_id, INACTIVITY_TIMEOUT)

    assert len(stale) == 0


def test_get_stale_members_identifies_inactive():
    """Test that inactive members are identified as stale."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")
    manager.add_member(room.room_id, "alice", "node2")

    # Manually set last_activity to an old timestamp
    old_time = (
        datetime.now(timezone.utc) - timedelta(seconds=INACTIVITY_TIMEOUT + 10)
    ).isoformat()
    room.member_info["alice"].last_activity = old_time

    stale = manager.get_stale_members(room.room_id, INACTIVITY_TIMEOUT)

    assert len(stale) == 1
    assert "alice" in stale


def test_update_member_activity():
    """Test updating member activity timestamp."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")
    manager.add_member(room.room_id, "alice")

    old_activity = room.member_info["alice"].last_activity

    import time

    time.sleep(0.01)

    result = manager.update_member_activity(room.room_id, "alice")

    assert result is True
    assert room.member_info["alice"].last_activity != old_activity


# Node Health Tracking Tests


def test_get_all_member_nodes():
    """Test getting all nodes with members."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")

    manager.add_member(room.room_id, "alice", "node2")
    manager.add_member(room.room_id, "bob", "node3")
    manager.add_member(room.room_id, "carol", "test_node")

    nodes = manager.get_all_member_nodes()

    # Should only include remote nodes (not test_node)
    assert "node2" in nodes
    assert "node3" in nodes
    assert "test_node" not in nodes


def test_record_heartbeat_creates_health_entry():
    """Test that recording heartbeat creates health entry."""
    manager = RoomStateManager(node_id="test_node")

    manager.record_node_heartbeat_success("node2")

    health = manager.get_node_health("node2")
    assert health is not None
    assert health.status == NodeStatus.HEALTHY


def test_record_heartbeat_failure_tracks_failures():
    """Test that heartbeat failures are tracked."""
    manager = RoomStateManager(node_id="test_node")

    manager.record_node_heartbeat_failure("node2")

    health = manager.get_node_health("node2")
    assert health.consecutive_failures == 1
    assert health.status == NodeStatus.DEGRADED


def test_get_failed_nodes():
    """Test getting list of failed nodes."""
    manager = RoomStateManager(node_id="test_node")

    # Mark node2 as failed (2 failures)
    manager.record_node_heartbeat_failure("node2")
    manager.record_node_heartbeat_failure("node2")

    # node3 is degraded but not failed
    manager.record_node_heartbeat_failure("node3")

    failed = manager.get_failed_nodes()

    assert "node2" in failed
    assert "node3" not in failed


def test_remove_all_members_from_node():
    """Test removing all members from a failed node."""
    manager = RoomStateManager(node_id="test_node")
    room1 = manager.create_room("Room 1", "creator")
    room2 = manager.create_room("Room 2", "creator")

    manager.add_member(room1.room_id, "alice", "node2")
    manager.add_member(room1.room_id, "bob", "node2")
    manager.add_member(room2.room_id, "carol", "node2")
    manager.add_member(room2.room_id, "dave", "node3")

    removed = manager.remove_all_members_from_node("node2")

    assert len(removed) == 3
    assert "alice" not in room1.members
    assert "bob" not in room1.members
    assert "carol" not in room2.members
    assert "dave" in room2.members  # Still there - different node


def test_room_get_all_nodes():
    """Test Room.get_all_nodes method."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room("Test Room", "creator")

    manager.add_member(room.room_id, "alice", "node2")
    manager.add_member(room.room_id, "bob", "node2")
    manager.add_member(room.room_id, "carol", "node3")

    nodes = room.get_all_nodes()

    assert len(nodes) == 2
    assert "node2" in nodes
    assert "node3" in nodes


# XML-RPC Method Tests


def test_xmlrpc_notify_member_disconnect_success():
    """Test XML-RPC notify_member_disconnect method."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    # Create a room and add a member
    room = room_manager.create_room("Test Room", "creator")
    room_manager.add_member(room.room_id, "alice", "node2")

    # Track broadcast calls
    broadcast_calls = []

    def mock_broadcast(room_id, message, exclude_user=None):
        broadcast_calls.append((room_id, message, exclude_user))

    server.set_broadcast_callback(mock_broadcast)

    # Call notify_member_disconnect
    result = server.notify_member_disconnect(
        room.room_id, "alice", "node2", "User disconnected"
    )

    assert result["success"] is True
    assert "alice" not in room.members
    assert len(broadcast_calls) == 1
    _, message, _ = broadcast_calls[0]
    assert message["type"] == "member_left"
    assert message["data"]["username"] == "alice"
    assert message["data"]["reason"] == "User disconnected"


def test_xmlrpc_notify_member_disconnect_room_not_found():
    """Test notify_member_disconnect with non-existent room."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    result = server.notify_member_disconnect(
        "non-existent-room", "alice", "node2", "User disconnected"
    )

    assert result["success"] is False
    assert "Room not found" in result["message"]


def test_xmlrpc_notify_member_disconnect_user_not_in_room():
    """Test notify_member_disconnect when user already gone."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    room = room_manager.create_room("Test Room", "creator")

    # User not in room
    result = server.notify_member_disconnect(
        room.room_id, "alice", "node2", "User disconnected"
    )

    # Should succeed - user already gone is not an error
    assert result["success"] is True


def test_xmlrpc_heartbeat():
    """Test XML-RPC heartbeat method."""
    room_manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=room_manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    result = server.heartbeat()

    assert result["status"] == "ok"
    assert result["node_id"] == "test_node"
    assert "timestamp" in result


# WebSocket Disconnect Handler Tests


@pytest.mark.asyncio
async def test_websocket_disconnect_removes_from_local_room():
    """Test that WebSocket disconnect removes user from local room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room and add a member
    room = room_manager.create_room("Test Room", "creator")
    room_manager.add_member(room.room_id, "alice")

    # Register a mock websocket
    mock_ws = MockWebSocket()
    ws_server.register_client_room_membership(
        mock_ws, room.room_id, "alice"
    )

    # Simulate disconnect
    await ws_server._handle_client_disconnect(mock_ws)

    # User should be removed
    assert "alice" not in room.members


@pytest.mark.asyncio
async def test_websocket_disconnect_broadcasts_member_left():
    """Test that disconnect broadcasts member_left to other members."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    room = room_manager.create_room("Test Room", "creator")
    room_manager.add_member(room.room_id, "alice")
    room_manager.add_member(room.room_id, "bob")

    # Register both websockets
    alice_ws = MockWebSocket()
    bob_ws = MockWebSocket()
    ws_server.register_client_room_membership(
        alice_ws, room.room_id, "alice"
    )
    ws_server.register_client_room_membership(bob_ws, room.room_id, "bob")

    # Alice disconnects
    await ws_server._handle_client_disconnect(alice_ws)

    # Bob should receive member_left notification
    assert len(bob_ws.sent_messages) == 1
    notification = json.loads(bob_ws.sent_messages[0])
    assert notification["type"] == "member_left"
    assert notification["data"]["username"] == "alice"
    assert notification["data"]["reason"] == "User disconnected"


@pytest.mark.asyncio
async def test_websocket_disconnect_no_error_when_not_in_room():
    """Test that disconnect doesn't error when client not in any room."""
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    mock_ws = MockWebSocket()

    # Should not raise any exception
    await ws_server._handle_client_disconnect(mock_ws)


# Integration Tests


def test_member_lifecycle_local():
    """Test complete member lifecycle for local room."""
    room_manager = RoomStateManager(node_id="test_node")
    room = room_manager.create_room("Test Room", "creator")

    # Join
    room_manager.add_member(room.room_id, "alice", "test_node")
    assert "alice" in room.members
    assert room.member_info["alice"].node_id == "test_node"

    # Activity
    room_manager.update_member_activity(room.room_id, "alice")

    # Leave
    room_manager.remove_member(room.room_id, "alice")
    assert "alice" not in room.members
    assert "alice" not in room.member_info


def test_member_lifecycle_remote():
    """Test complete member lifecycle for remote member."""
    room_manager = RoomStateManager(node_id="test_node")
    room = room_manager.create_room("Test Room", "creator")

    # Join from remote node
    room_manager.add_member(room.room_id, "alice", "node2")
    assert "alice" in room.members
    assert room.member_info["alice"].node_id == "node2"

    # Check node health tracking was initialized
    health = room_manager.get_node_health("node2")
    assert health is not None

    # Leave
    room_manager.remove_member(room.room_id, "alice")
    assert "alice" not in room.members
