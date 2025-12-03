"""
Tests for Room Deletion with Two-Phase Commit (2PC)

Tests for the distributed room deletion functionality including
coordinator and participant behavior in the 2PC protocol.
"""

import json
import pytest
from src.node import (
    RoomStateManager,
    WebSocketServer,
    XMLRPCServer,
    RoomState,
    TransactionState,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


class MockPeerRegistry:
    """Mock PeerRegistry for testing."""

    def __init__(self, peers=None):
        self._peers = peers or {}

    def list_peers(self):
        return self._peers.copy()

    def get_peer_address(self, node_id):
        return self._peers.get(node_id)


# ===== Room State Tests =====


def test_room_has_state():
    """Test that rooms have a state attribute."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    assert room.state == RoomState.ACTIVE


def test_room_state_transitions():
    """Test room state transitions during 2PC."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # Start deletion transaction
    transaction = manager.start_deletion_transaction(
        room.room_id, ["node2", "node3"]
    )
    assert transaction is not None
    assert room.state == RoomState.DELETION_PENDING

    # Transition to commit
    manager.transition_to_commit(transaction.transaction_id)
    assert room.state == RoomState.COMMITTING


def test_room_state_rollback():
    """Test room state returns to ACTIVE after rollback."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # Start deletion transaction
    transaction = manager.start_deletion_transaction(room.room_id, ["node2"])
    assert room.state == RoomState.DELETION_PENDING

    # Rollback
    manager.rollback_deletion(transaction.transaction_id)
    assert room.state == RoomState.ACTIVE


def test_room_to_dict_includes_creator():
    """Test that room.to_dict() includes creator_id."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="alice")
    room_dict = room.to_dict()
    assert "creator_id" in room_dict
    assert room_dict["creator_id"] == "alice"


# ===== Deletion Transaction Tests =====


def test_start_deletion_transaction():
    """Test starting a 2PC deletion transaction."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    transaction = manager.start_deletion_transaction(
        room.room_id, ["node2", "node3"]
    )

    assert transaction is not None
    assert transaction.room_id == room.room_id
    assert transaction.state == TransactionState.PREPARE
    assert "node2" in transaction.participants
    assert "node3" in transaction.participants
    assert all(v is None for v in transaction.votes.values())


def test_start_deletion_transaction_nonexistent_room():
    """Test that starting deletion on nonexistent room returns None."""
    manager = RoomStateManager(node_id="test_node")

    transaction = manager.start_deletion_transaction(
        "nonexistent-room", ["node2"]
    )

    assert transaction is None


def test_start_deletion_transaction_already_pending():
    """Test that starting deletion on pending room returns None."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # Start first transaction
    manager.start_deletion_transaction(room.room_id, ["node2"])

    # Try to start second transaction
    second = manager.start_deletion_transaction(room.room_id, ["node3"])
    assert second is None


def test_record_vote():
    """Test recording votes from participants."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    transaction = manager.start_deletion_transaction(
        room.room_id, ["node2", "node3"]
    )

    # Record votes
    result = manager.record_vote(transaction.transaction_id, "node2", "READY")
    assert result is True
    assert transaction.votes["node2"] == "READY"

    result = manager.record_vote(transaction.transaction_id, "node3", "ABORT")
    assert result is True
    assert transaction.votes["node3"] == "ABORT"


def test_all_votes_ready():
    """Test checking if all votes are READY."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    transaction = manager.start_deletion_transaction(
        room.room_id, ["node2", "node3"]
    )

    # No votes yet
    assert manager.all_votes_ready(transaction.transaction_id) is False

    # One READY vote
    manager.record_vote(transaction.transaction_id, "node2", "READY")
    assert manager.all_votes_ready(transaction.transaction_id) is False

    # All READY
    manager.record_vote(transaction.transaction_id, "node3", "READY")
    assert manager.all_votes_ready(transaction.transaction_id) is True


def test_all_votes_ready_with_abort():
    """Test that one ABORT makes all_votes_ready return False."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    transaction = manager.start_deletion_transaction(
        room.room_id, ["node2", "node3"]
    )

    manager.record_vote(transaction.transaction_id, "node2", "READY")
    manager.record_vote(transaction.transaction_id, "node3", "ABORT")

    assert manager.all_votes_ready(transaction.transaction_id) is False


def test_complete_deletion():
    """Test completing a deletion transaction."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    room_id = room.room_id

    transaction = manager.start_deletion_transaction(room_id, [])
    manager.transition_to_commit(transaction.transaction_id)

    # Complete the deletion
    result = manager.complete_deletion(transaction.transaction_id)
    assert result is True

    # Room should be deleted
    assert manager.get_room(room_id) is None


# ===== Participant-side 2PC Tests =====


def test_prepare_for_deletion_ready():
    """Test participant preparing for deletion (voting READY)."""
    manager = RoomStateManager(node_id="participant_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    result = manager.prepare_for_deletion(
        room.room_id, "txn-123", "coordinator_node"
    )

    assert result["vote"] == "READY"
    assert result["node_id"] == "participant_node"
    assert room.state == RoomState.DELETION_PENDING


def test_prepare_for_deletion_nonexistent_room():
    """Test preparing for deletion when room doesn't exist locally."""
    manager = RoomStateManager(node_id="participant_node")

    result = manager.prepare_for_deletion(
        "nonexistent-room", "txn-123", "coordinator_node"
    )

    # Should vote READY since nothing to delete locally - this is safe in 2PC
    # as it means no local cleanup is needed on this participant node
    assert result["vote"] == "READY"


def test_prepare_for_deletion_already_pending():
    """Test preparing when room is already in deletion pending state."""
    manager = RoomStateManager(node_id="participant_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # First prepare
    manager.prepare_for_deletion(room.room_id, "txn-1", "coordinator")

    # Second prepare should fail
    result = manager.prepare_for_deletion(room.room_id, "txn-2", "coordinator")

    assert result["vote"] == "ABORT"
    assert "DELETION_PENDING" in result.get("reason", "")


def test_commit_deletion_participant():
    """Test participant committing deletion."""
    manager = RoomStateManager(node_id="participant_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    room_id = room.room_id

    # Prepare first
    manager.prepare_for_deletion(room_id, "txn-123", "coordinator")

    # Commit
    result = manager.commit_deletion(room_id, "txn-123")

    assert result["success"] is True
    assert manager.get_room(room_id) is None


def test_rollback_deletion_participant():
    """Test participant rolling back deletion."""
    manager = RoomStateManager(node_id="participant_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    room_id = room.room_id

    # Prepare first
    manager.prepare_for_deletion(room_id, "txn-123", "coordinator")
    assert room.state == RoomState.DELETION_PENDING

    # Rollback
    result = manager.rollback_deletion_participant(room_id, "txn-123")

    assert result["success"] is True
    assert room.state == RoomState.ACTIVE


def test_can_operate_on_room():
    """Test can_operate_on_room returns False during deletion."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    # Can operate on active room
    assert manager.can_operate_on_room(room.room_id) is True

    # Start deletion
    manager.start_deletion_transaction(room.room_id, [])

    # Cannot operate during deletion
    assert manager.can_operate_on_room(room.room_id) is False


# ===== XML-RPC Server Tests =====


def test_xmlrpc_prepare_delete_room():
    """Test XML-RPC prepare_delete_room method."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")

    server = XMLRPCServer(manager, "localhost", 9090, "http://localhost:9090")

    result = server.prepare_delete_room(
        room.room_id, "txn-123", "coordinator_node"
    )

    assert result["vote"] == "READY"
    assert result["node_id"] == "test_node"


def test_xmlrpc_commit_delete_room():
    """Test XML-RPC commit_delete_room method."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    room_id = room.room_id

    server = XMLRPCServer(manager, "localhost", 9090, "http://localhost:9090")

    # Prepare first
    server.prepare_delete_room(room_id, "txn-123", "coordinator")

    # Commit
    result = server.commit_delete_room(room_id, "txn-123")

    assert result["success"] is True
    assert manager.get_room(room_id) is None


def test_xmlrpc_rollback_delete_room():
    """Test XML-RPC rollback_delete_room method."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="user1")
    room_id = room.room_id

    server = XMLRPCServer(manager, "localhost", 9090, "http://localhost:9090")

    # Prepare first
    server.prepare_delete_room(room_id, "txn-123", "coordinator")

    # Rollback
    result = server.rollback_delete_room(room_id, "txn-123")

    assert result["success"] is True
    assert room.state == RoomState.ACTIVE


# ===== WebSocket Server Tests =====


@pytest.mark.asyncio
async def test_websocket_delete_room_not_creator():
    """Test that non-creator cannot delete room."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="alice")

    ws_server = WebSocketServer(manager, "localhost", 8080)
    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "delete_room",
            "data": {
                "room_id": room.room_id,
                "username": "bob",  # Not the creator
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "delete_room_failed"
    assert response["data"]["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_websocket_delete_room_not_found():
    """Test deleting nonexistent room."""
    manager = RoomStateManager(node_id="test_node")

    ws_server = WebSocketServer(manager, "localhost", 8080)
    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "delete_room",
            "data": {
                "room_id": "nonexistent-room",
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "delete_room_failed"
    assert response["data"]["error_code"] == "ROOM_NOT_FOUND"


@pytest.mark.asyncio
async def test_websocket_delete_room_success_no_peers():
    """Test successful deletion with no peer nodes."""
    manager = RoomStateManager(node_id="test_node")
    room = manager.create_room(room_name="Test Room", creator_id="alice")
    room_id = room.room_id

    # No peer registry means no participants
    ws_server = WebSocketServer(manager, "localhost", 8080)
    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "delete_room",
            "data": {
                "room_id": room_id,
                "username": "alice",
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    # Should receive initiated and success responses
    assert len(mock_ws.sent_messages) >= 2

    # First should be initiated
    initiated = json.loads(mock_ws.sent_messages[0])
    assert initiated["type"] == "delete_room_initiated"

    # Last should be success
    success = json.loads(mock_ws.sent_messages[-1])
    assert success["type"] == "delete_room_success"

    # Room should be deleted
    assert manager.get_room(room_id) is None


@pytest.mark.asyncio
async def test_websocket_delete_room_missing_fields():
    """Test delete_room with missing required fields."""
    manager = RoomStateManager(node_id="test_node")

    ws_server = WebSocketServer(manager, "localhost", 8080)
    mock_ws = MockWebSocket()

    request = json.dumps(
        {
            "type": "delete_room",
            "data": {
                "room_id": "some-room",
                # Missing username
            },
        }
    )

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])
    assert response["type"] == "delete_room_failed"
    assert response["data"]["error_code"] == "INVALID_REQUEST"
