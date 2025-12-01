import asyncio
from datetime import datetime

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone

from src.node import PeerRegistry
from src.node.websocket_server import WebSocketServer
from src.node.room_state import RoomStateManager, Room
from src.node.xmlrpc_server import XMLRPCServer

@pytest.mark.asyncio
async def test_handle_client_disconnect_remote_admin():
    # setup
    room_manager = RoomStateManager(node_id="test_node")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create a room
    room = room_manager.create_room(
        room_name="Test Room", creator_id="creator", description="A test room"
    )
    room.room_id = "room1"
    room.admin_node = "nodeA"
    room.members.add("user1")
    room_manager._rooms["room1"] = room

    # Fake websocket object
    ws_obj = object()

    # Register membership so handle_client_disconnect finds it
    ws_server._room_clients["room1"] = {(ws_obj, "user1")}
    ws_server._client_rooms[ws_obj] = {"room1"}

    # get_room_admin must return dict with address + node_id
    ws_server.get_room_admin = MagicMock(
        return_value={"address": "http://nodeA/xml", "node_id": "nodeA"}
    )
    ws_server.broadcast_member_left = MagicMock()

    # Mock xmlrpc ServerProxy
    notify_mock = MagicMock()
    cleanup_mock = MagicMock()

    with patch(
        "src.node.websocket_server.xmlrpc.client.ServerProxy"
    ) as mock_proxy:
        mock_proxy.return_value.notify_member_disconnect = notify_mock
        mock_proxy.return_value.cleanup_stale_members = cleanup_mock

        # run
        await ws_server.handle_client_disconnect(ws_obj)

        notify_mock.assert_called_once_with("room1", "user1", "test_node")
        cleanup_mock.assert_called_once_with("room1")
        ws_server.broadcast_member_left.assert_not_called()


@pytest.mark.asyncio
async def test_handle_client_disconnect_local_admin():
    room_manager = RoomStateManager(node_id="nodeA")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # Create room where THIS node is admin
    room = room_manager.create_room("Test Room", "creator", "desc")
    room.room_id = "room1"
    room.admin_node = "nodeA"
    room.members.add("bob")
    room_manager._rooms["room1"] = room

    # Fake websocket tied to bob
    ws_bob = object()

    ws_server._room_clients["room1"] = {(ws_bob, "bob")}
    ws_server._client_rooms[ws_bob] = {"room1"}

    ws_server.broadcast_member_left = MagicMock()

    await ws_server.handle_client_disconnect(ws_bob)

    assert "bob" not in room.members
    ws_server.broadcast_member_left.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_member_left():
    room_manager = RoomStateManager(node_id="nodeA")
    ws_server = WebSocketServer(room_manager, "localhost", 9000)

    # create room
    room = room_manager.create_room("TestRoom", "creator", "desc")
    room.room_id = "room1"
    room.admin_node = "nodeA"
    room_manager._rooms["room1"] = room

    # mock websockets with AsyncMock
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    ws_server._room_clients["room1"] = {(ws1, "alice"), (ws2, "bob")}

    # run
    ws_server.broadcast_member_left("room1", "alice", "User disconnected")

    # Let async tasks run
    await asyncio.sleep(0)

    ws1.send.assert_called()
    ws2.send.assert_called()

@pytest.mark.asyncio
def test_notify_member_disconnect_local_admin():
    room_manager = RoomStateManager(node_id="nodeA")
    peer_reg = PeerRegistry(node_id="nodeA")
    server = XMLRPCServer(room_manager, "localhost", 10000, "nodeA", peer_registry=peer_reg)

    room = Room("room1", "TestRoom", "desc", admin_node="nodeA", created_at=datetime.now(), creator_id="creator", members=[])
    room.members.append("bob")
    room_manager._rooms["room1"] = room

    server._broadcast_callback = MagicMock()

    result = server.notify_member_disconnect("room1", "bob", "nodeA")

    assert result is True
    assert "bob" not in room.members
    server._broadcast_callback.assert_called_once()

@pytest.mark.asyncio
async def test_heartbeat_monitor_marks_node_failed():
    room_manager = RoomStateManager(node_id="nodeA")
    peer_reg = PeerRegistry(node_id="nodeA")
    peer_reg.register_peer("nodeB", "http://example.com")  # or whatever your peer API is

    server = XMLRPCServer(room_manager, "localhost", 9000, "nodeA", peer_registry=peer_reg)

    server.node_health["nodeB"] = {
        "status": "healthy",
        "consecutive_failures": 1,
        "last_active": None,
    }

    with patch(
        "src.node.websocket_server.xmlrpc.client.ServerProxy",
        side_effect=Exception("node down")
    ):
        with patch.object(server, "handle_node_failure", AsyncMock()) as failure_mock:
            async def stop(*args, **kwargs):
                raise StopAsyncIteration

            with patch("asyncio.sleep", side_effect=stop):
                try:
                    await server.heartbeat_monitor()
                except StopAsyncIteration:
                    pass

                assert server.node_health["nodeB"]["status"] == "failed"
                failure_mock.assert_called_once_with("nodeB")

@pytest.mark.asyncio
async def test_handle_node_failure_removes_members():
    room_manager = RoomStateManager(node_id="nodeA")
    peer_reg = PeerRegistry(node_id="nodeA")
    server = XMLRPCServer(room_manager, "localhost", 9000, "nodeA", peer_registry=peer_reg)

    room = Room(
        "room1",
        "TestRoom",
        "desc",
        admin_node="nodeA",
        created_at=datetime.now(),
        creator_id="creator",
        members=set()
    )

    room.members.add("user1")
    room.members.add("user2")

    room_manager._rooms["room1"] = room

    server._broadcast_callback = MagicMock()

    await server.handle_node_failure("nodeA")

    # Admin failure → all local members removed
    assert room.members == set()

    # Broadcast sent for each removed user
    assert server._broadcast_callback.call_count == 2

    # Optional: verify correct order/content
    calls = server._broadcast_callback.call_args_list
    assert calls[0].args[0] == "room1"
    assert calls[1].args[0] == "room1"

