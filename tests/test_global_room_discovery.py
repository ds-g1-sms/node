"""
Tests for Global Room Discovery

Tests for XML-RPC server, peer registry, and global room discovery.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future

from src.node import (
    RoomStateManager,
    WebSocketServer,
    XMLRPCServer,
    PeerRegistry,
)


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


def test_xmlrpc_server_can_be_created():
    """Test that XMLRPCServer can be created."""
    manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )
    assert server is not None
    assert server.room_manager == manager
    assert server.host == "localhost"
    assert server.port == 9090
    assert server.node_address == "http://localhost:9090"


def test_xmlrpc_get_hosted_rooms_empty():
    """Test XML-RPC get_hosted_rooms with no rooms."""
    manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    rooms = server.get_hosted_rooms()
    assert rooms == []


def test_xmlrpc_get_hosted_rooms_with_rooms():
    """Test XML-RPC get_hosted_rooms with rooms."""
    manager = RoomStateManager(node_id="test_node")
    server = XMLRPCServer(
        room_manager=manager,
        host="localhost",
        port=9090,
        node_address="http://localhost:9090",
    )

    # Create some rooms
    manager.create_room(
        room_name="Room 1", creator_id="user1", description="First room"
    )
    manager.create_room(
        room_name="Room 2", creator_id="user2", description="Second room"
    )

    rooms = server.get_hosted_rooms()
    assert len(rooms) == 2

    # Check room structure includes node_address
    room1 = next(r for r in rooms if r["room_name"] == "Room 1")
    assert room1["room_name"] == "Room 1"
    assert room1["description"] == "First room"
    assert room1["member_count"] == 1
    assert room1["admin_node"] == "test_node"
    assert room1["node_address"] == "http://localhost:9090"


def test_peer_registry_can_be_created():
    """Test that PeerRegistry can be created."""
    registry = PeerRegistry(node_id="node1")
    assert registry is not None
    assert registry.node_id == "node1"
    assert registry.list_peers() == {}


def test_peer_registry_register_peer():
    """Test registering a peer node."""
    registry = PeerRegistry(node_id="node1")

    registry.register_peer("node2", "http://node2:9090")
    registry.register_peer("node3", "http://node3:9090")

    peers = registry.list_peers()
    assert len(peers) == 2
    assert peers["node2"] == "http://node2:9090"
    assert peers["node3"] == "http://node3:9090"


def test_peer_registry_get_peer_address():
    """Test getting peer address."""
    registry = PeerRegistry(node_id="node1")
    registry.register_peer("node2", "http://node2:9090")

    address = registry.get_peer_address("node2")
    assert address == "http://node2:9090"

    # Non-existent peer
    address = registry.get_peer_address("node99")
    assert address is None


@patch("src.node.peer_registry.ServerProxy")
def test_peer_registry_query_peer_rooms(mock_server_proxy):
    """Test querying a peer for rooms."""
    registry = PeerRegistry(node_id="node1")

    # Mock the XML-RPC proxy
    mock_proxy = Mock()
    mock_proxy.get_hosted_rooms.return_value = [
        {
            "room_id": "room1",
            "room_name": "Test Room",
            "description": "A test",
            "member_count": 1,
            "admin_node": "node2",
            "node_address": "http://node2:9090",
        }
    ]
    mock_server_proxy.return_value = mock_proxy

    rooms = registry.query_peer_rooms("node2", "http://node2:9090")

    assert len(rooms) == 1
    assert rooms[0]["room_name"] == "Test Room"
    assert rooms[0]["admin_node"] == "node2"


@patch("src.node.peer_registry.ServerProxy")
def test_peer_registry_query_peer_rooms_failure(mock_server_proxy):
    """Test querying a peer that fails."""
    registry = PeerRegistry(node_id="node1")

    # Mock the XML-RPC proxy to raise exception
    mock_proxy = Mock()
    mock_proxy.get_hosted_rooms.side_effect = Exception("Connection failed")
    mock_server_proxy.return_value = mock_proxy

    with pytest.raises(Exception):
        registry.query_peer_rooms("node2", "http://node2:9090")


@patch("src.node.peer_registry.ThreadPoolExecutor")
@patch("src.node.peer_registry.ServerProxy")
def test_peer_registry_discover_global_rooms(
    mock_server_proxy, mock_executor
):
    """Test global room discovery."""
    registry = PeerRegistry(node_id="node1")
    registry.register_peer("node2", "http://node2:9090")
    registry.register_peer("node3", "http://node3:9090")

    local_rooms = [
        {
            "room_id": "room1",
            "room_name": "Local Room",
            "description": "Local",
            "member_count": 1,
            "admin_node": "node1",
            "node_address": "http://node1:9090",
        }
    ]

    # Mock the executor and futures
    mock_future1 = Mock(spec=Future)
    mock_future1.result.return_value = [
        {
            "room_id": "room2",
            "room_name": "Room 2",
            "description": "From node2",
            "member_count": 2,
            "admin_node": "node2",
            "node_address": "http://node2:9090",
        }
    ]

    mock_future2 = Mock(spec=Future)
    mock_future2.result.return_value = [
        {
            "room_id": "room3",
            "room_name": "Room 3",
            "description": "From node3",
            "member_count": 3,
            "admin_node": "node3",
            "node_address": "http://node3:9090",
        }
    ]

    # Mock the executor context manager
    mock_executor_instance = MagicMock()
    mock_executor_instance.__enter__.return_value = mock_executor_instance
    mock_executor_instance.submit.side_effect = [mock_future1, mock_future2]

    # Mock as_completed
    with patch(
        "src.node.peer_registry.as_completed",
        return_value=[mock_future1, mock_future2],
    ):
        mock_executor.return_value = mock_executor_instance

        # Create a mapping for future_to_node
        def submit_side_effect(func, *args):
            if args[0] == "node2":
                return mock_future1
            elif args[0] == "node3":
                return mock_future2

        mock_executor_instance.submit.side_effect = submit_side_effect

        result = registry.discover_global_rooms(local_rooms)

        assert result["total_count"] == 3
        assert len(result["rooms"]) == 3
        assert len(result["nodes_available"]) == 3
        assert len(result["nodes_unavailable"]) == 0
        assert "node1" in result["nodes_available"]


def test_peer_registry_discover_global_rooms_no_peers():
    """Test global room discovery with no peers."""
    registry = PeerRegistry(node_id="node1")

    local_rooms = [
        {
            "room_id": "room1",
            "room_name": "Local Room",
            "description": "Local",
            "member_count": 1,
            "admin_node": "node1",
        }
    ]

    result = registry.discover_global_rooms(local_rooms)

    assert result["total_count"] == 1
    assert len(result["rooms"]) == 1
    assert result["nodes_available"] == ["node1"]
    assert result["nodes_unavailable"] == []


@pytest.mark.asyncio
async def test_websocket_discover_rooms_without_peer_registry():
    """Test discover_rooms without peer registry (falls back to local)."""
    manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(
        room_manager=manager,
        host="localhost",
        port=9000,
        peer_registry=None,
    )

    # Create a room
    manager.create_room(
        room_name="Local Room", creator_id="user1", description="Local only"
    )

    mock_ws = MockWebSocket()

    request = json.dumps({"type": "discover_rooms", "scope": "global"})

    await ws_server.process_message(mock_ws, request)

    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])

    assert response["type"] == "global_rooms_list"
    assert response["data"]["total_count"] == 1
    assert len(response["data"]["rooms"]) == 1
    assert response["data"]["rooms"][0]["room_name"] == "Local Room"
    assert response["data"]["nodes_available"] == ["test_node"]
    assert response["data"]["nodes_unavailable"] == []


@pytest.mark.asyncio
async def test_websocket_discover_rooms_with_peer_registry():
    """Test discover_rooms with peer registry."""
    manager = RoomStateManager(node_id="node1")
    peer_registry = PeerRegistry(node_id="node1")

    ws_server = WebSocketServer(
        room_manager=manager,
        host="localhost",
        port=9000,
        peer_registry=peer_registry,
    )

    # Create a local room
    manager.create_room(
        room_name="Local Room", creator_id="user1", description="Local"
    )

    # Mock the peer registry's discover_global_rooms method
    mock_result = {
        "rooms": [
            {
                "room_id": "room1",
                "room_name": "Local Room",
                "description": "Local",
                "member_count": 1,
                "admin_node": "node1",
            },
            {
                "room_id": "room2",
                "room_name": "Remote Room",
                "description": "Remote",
                "member_count": 2,
                "admin_node": "node2",
            },
        ],
        "total_count": 2,
        "nodes_queried": ["node1", "node2"],
        "nodes_available": ["node1", "node2"],
        "nodes_unavailable": [],
    }

    with patch.object(
        peer_registry, "discover_global_rooms", return_value=mock_result
    ):
        mock_ws = MockWebSocket()

        request = json.dumps({"type": "discover_rooms", "scope": "global"})

        await ws_server.process_message(mock_ws, request)

        assert len(mock_ws.sent_messages) == 1
        response = json.loads(mock_ws.sent_messages[0])

        assert response["type"] == "global_rooms_list"
        assert response["data"]["total_count"] == 2
        assert len(response["data"]["rooms"]) == 2
        assert response["data"]["nodes_available"] == ["node1", "node2"]
        assert response["data"]["nodes_unavailable"] == []


@pytest.mark.asyncio
async def test_websocket_discover_rooms_with_unavailable_nodes():
    """Test discover_rooms with some unavailable nodes."""
    manager = RoomStateManager(node_id="node1")
    peer_registry = PeerRegistry(node_id="node1")

    ws_server = WebSocketServer(
        room_manager=manager,
        host="localhost",
        port=9000,
        peer_registry=peer_registry,
    )

    # Create a local room
    manager.create_room(
        room_name="Local Room", creator_id="user1", description="Local"
    )

    # Mock the peer registry's discover_global_rooms method
    mock_result = {
        "rooms": [
            {
                "room_id": "room1",
                "room_name": "Local Room",
                "description": "Local",
                "member_count": 1,
                "admin_node": "node1",
            },
        ],
        "total_count": 1,
        "nodes_queried": ["node1", "node2", "node3"],
        "nodes_available": ["node1"],
        "nodes_unavailable": ["node2", "node3"],
    }

    with patch.object(
        peer_registry, "discover_global_rooms", return_value=mock_result
    ):
        mock_ws = MockWebSocket()

        request = json.dumps({"type": "discover_rooms"})

        await ws_server.process_message(mock_ws, request)

        assert len(mock_ws.sent_messages) == 1
        response = json.loads(mock_ws.sent_messages[0])

        assert response["type"] == "global_rooms_list"
        assert response["data"]["total_count"] == 1
        assert response["data"]["nodes_available"] == ["node1"]
        assert response["data"]["nodes_unavailable"] == ["node2", "node3"]
