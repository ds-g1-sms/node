#!/usr/bin/env python3
"""
Distributed Chat Node Server

A distributed peer-to-peer chat system node server.
"""

import logging
import sys
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from xmlrpc.client import ServerProxy

from .room_state import (
    RoomStateManager,
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    INACTIVITY_TIMEOUT,
    CLEANUP_INTERVAL,
)
from .websocket_server import WebSocketServer
from .xmlrpc_server import XMLRPCServer
from .peer_registry import PeerRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_server(
    node_id: str,
    ws_host: str,
    ws_port: int,
    xmlrpc_host: str,
    xmlrpc_port: int,
    xmlrpc_address: str,
    peer_nodes: dict,
):
    """
    Run the node server with WebSocket and XML-RPC support.

    Args:
        node_id: Unique identifier for this node
        ws_host: WebSocket host address to bind to
        ws_port: WebSocket port to listen on
        xmlrpc_host: XML-RPC host address to bind to
        xmlrpc_port: XML-RPC port to listen on
        xmlrpc_address: Full XML-RPC address of this node
        peer_nodes: Dictionary of peer nodes {node_id: xmlrpc_address}
    """
    # Initialize room state manager
    room_manager = RoomStateManager(node_id)

    # Initialize peer registry
    peer_registry = PeerRegistry(node_id)
    for peer_id, peer_addr in peer_nodes.items():
        peer_registry.register_peer(peer_id, peer_addr)

    # Initialize XML-RPC server
    xmlrpc_server = XMLRPCServer(
        room_manager, xmlrpc_host, xmlrpc_port, xmlrpc_address, peer_registry
    )

    # Initialize WebSocket server
    ws_server = WebSocketServer(room_manager, ws_host, ws_port, peer_registry)

    # Connect XML-RPC broadcast callback to WebSocket server
    xmlrpc_server.set_broadcast_callback(ws_server.broadcast_to_room_sync)

    # Start the XML-RPC server
    xmlrpc_server.start()

    # Start the WebSocket server
    await ws_server.start()

    logger.info(f"Node server '{node_id}' is ready")
    logger.info(f"WebSocket server listening on ws://{ws_host}:{ws_port}")
    logger.info(f"XML-RPC server listening at {xmlrpc_address}")
    logger.info(f"Registered {len(peer_nodes)} peer nodes")

    # Create background tasks for health monitoring
    heartbeat_task = asyncio.create_task(
        heartbeat_monitor(room_manager, peer_registry, ws_server)
    )
    cleanup_task = asyncio.create_task(
        stale_member_cleanup(room_manager, ws_server, peer_registry)
    )

    # Keep server running
    try:
        # Wait indefinitely
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        # Cancel background tasks
        heartbeat_task.cancel()
        cleanup_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        # Stop servers
        await ws_server.stop()
        xmlrpc_server.stop()
        logger.info("Node server stopped")


async def heartbeat_monitor(
    room_manager: RoomStateManager,
    peer_registry: PeerRegistry,
    ws_server: WebSocketServer,
):
    """
    Periodic task to send heartbeats to member nodes.

    Runs every HEARTBEAT_INTERVAL seconds to check node health.
    When a node fails to respond, removes all its members from rooms.

    Args:
        room_manager: The room state manager
        peer_registry: The peer registry for node addresses
        ws_server: The WebSocket server for broadcasting
    """
    logger.info("Starting heartbeat monitor task")

    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            # Get all nodes with members in rooms we administer
            member_nodes = room_manager.get_all_member_nodes()

            if not member_nodes:
                continue

            # Check health of each node
            for node_id in member_nodes:
                if node_id == room_manager.node_id:
                    continue  # Skip self

                # Get node address from peer registry
                node_addr = peer_registry.get_peer_address(node_id)
                if not node_addr:
                    logger.warning(
                        f"No address found for node {node_id}, "
                        f"skipping heartbeat"
                    )
                    continue

                # Send heartbeat
                is_healthy = await _send_heartbeat(node_addr)

                if is_healthy:
                    room_manager.record_node_heartbeat_success(node_id)
                else:
                    is_failed = room_manager.record_node_heartbeat_failure(
                        node_id
                    )
                    if is_failed:
                        # Node is down - remove all its members
                        logger.warning(
                            f"Node {node_id} marked as failed, "
                            f"removing its members"
                        )
                        await _handle_node_failure(
                            room_manager, ws_server, peer_registry, node_id
                        )

        except asyncio.CancelledError:
            logger.info("Heartbeat monitor task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}")


async def _send_heartbeat(node_addr: str) -> bool:
    """
    Send heartbeat to a node to verify it's alive.

    Args:
        node_addr: Address of node to ping

    Returns:
        bool: True if node responded, False otherwise
    """
    loop = asyncio.get_running_loop()

    def _do_heartbeat():
        try:
            proxy = ServerProxy(node_addr, allow_none=True)
            # Note: We can't set timeout directly on ServerProxy,
            # but the call should timeout relatively quickly on network failure
            response = proxy.heartbeat()
            return response.get("status") == "ok"
        except Exception as e:
            logger.debug(f"Heartbeat to {node_addr} failed: {e}")
            return False

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await asyncio.wait_for(
                loop.run_in_executor(executor, _do_heartbeat),
                timeout=HEARTBEAT_TIMEOUT,
            )
            return result
    except asyncio.TimeoutError:
        logger.debug(f"Heartbeat to {node_addr} timed out")
        return False


async def _handle_node_failure(
    room_manager: RoomStateManager,
    ws_server: WebSocketServer,
    peer_registry: PeerRegistry,
    node_id: str,
):
    """
    Handle a node failure by removing all its members from all rooms.

    Args:
        room_manager: The room state manager
        ws_server: The WebSocket server for broadcasting
        peer_registry: The peer registry for broadcasting to other peers
        node_id: The failed node's ID
    """
    # Remove all members from the failed node
    removed = room_manager.remove_all_members_from_node(node_id)

    logger.info(f"Removed {len(removed)} members from failed node {node_id}")

    # Broadcast member_left for each removed member
    for room_id, username in removed:
        room = room_manager.get_room(room_id)
        member_count = len(room.members) if room else 0

        event_data = {
            "room_id": room_id,
            "username": username,
            "reason": "Node unreachable",
            "member_count": member_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Broadcast to local WebSocket clients
        broadcast_msg = {"type": "member_left", "data": event_data}
        ws_server.broadcast_to_room_sync(room_id, broadcast_msg)

        # Broadcast to other peer nodes
        peers = peer_registry.list_peers()
        for peer_node_id, peer_addr in peers.items():
            if peer_node_id == node_id:
                continue  # Skip the failed node
            try:
                proxy = ServerProxy(peer_addr, allow_none=True)
                proxy.receive_member_event_broadcast(
                    room_id, "member_left", event_data
                )
            except Exception as e:
                logger.error(
                    f"Failed to broadcast member_left to {peer_node_id}: {e}"
                )


async def stale_member_cleanup(
    room_manager: RoomStateManager,
    ws_server: WebSocketServer,
    peer_registry: PeerRegistry,
):
    """
    Periodic task to remove inactive members.

    Runs every CLEANUP_INTERVAL seconds to check for stale connections.

    Args:
        room_manager: The room state manager
        ws_server: The WebSocket server for broadcasting
        peer_registry: The peer registry for broadcasting to other peers
    """
    logger.info("Starting stale member cleanup task")

    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)

            # Check each room for stale members
            rooms = room_manager.list_rooms()

            for room_info in rooms:
                room_id = room_info.get("room_id")
                if not room_id:
                    continue

                # Get stale members for this room
                stale_members = room_manager.get_stale_members(
                    room_id, INACTIVITY_TIMEOUT
                )

                if not stale_members:
                    continue

                logger.info(
                    f"Found {len(stale_members)} stale members in "
                    f"room {room_id}: {stale_members}"
                )

                # Remove stale members
                for username in stale_members:
                    room_manager.remove_member(room_id, username)

                    room = room_manager.get_room(room_id)
                    member_count = len(room.members) if room else 0

                    event_data = {
                        "room_id": room_id,
                        "username": username,
                        "reason": "Connection timeout",
                        "member_count": member_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    # Broadcast to local WebSocket clients
                    broadcast_msg = {"type": "member_left", "data": event_data}
                    ws_server.broadcast_to_room_sync(room_id, broadcast_msg)

                    # Broadcast to peer nodes
                    peers = peer_registry.list_peers()
                    for peer_node_id, peer_addr in peers.items():
                        try:
                            proxy = ServerProxy(peer_addr, allow_none=True)
                            proxy.receive_member_event_broadcast(
                                room_id, "member_left", event_data
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to broadcast member_left to "
                                f"{peer_node_id}: {e}"
                            )

                    logger.info(
                        f"Removed stale member {username} from room {room_id}"
                    )

        except asyncio.CancelledError:
            logger.info("Stale member cleanup task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in stale member cleanup: {e}")


def main():
    """Main entry point for the node server."""
    logger.info("Starting distributed chat node server...")

    # Get configuration from environment or use defaults
    node_id = os.environ.get("NODE_ID", "node1")

    # WebSocket configuration
    ws_host = os.environ.get("WEBSOCKET_HOST", "0.0.0.0")
    ws_port = int(os.environ.get("WEBSOCKET_PORT", "8080"))

    # XML-RPC configuration
    xmlrpc_host = os.environ.get("XMLRPC_HOST", "0.0.0.0")
    xmlrpc_port = int(os.environ.get("XMLRPC_PORT", "9090"))
    xmlrpc_address = os.environ.get(
        "XMLRPC_ADDRESS", f"http://{node_id}:{xmlrpc_port}"
    )

    # Parse peer nodes from environment
    # Format: PEER_NODES=node2:http://node2:9090,node3:http://node3:9090
    peer_nodes = {}
    peer_nodes_env = os.environ.get("PEER_NODES", "")
    if peer_nodes_env:
        for peer_spec in peer_nodes_env.split(","):
            if ":" in peer_spec:
                parts = peer_spec.split(":", 1)
                if len(parts) == 2:
                    peer_id, peer_addr = parts[0].strip(), parts[1].strip()
                    # Handle the case where address has http://
                    if not peer_addr.startswith("http://"):
                        # Assume format is node_id:node_host:port
                        addr_parts = peer_spec.split(":")
                        if len(addr_parts) >= 3:
                            peer_id = addr_parts[0]
                            peer_host = addr_parts[1]
                            peer_port = addr_parts[2]
                            peer_addr = f"http://{peer_host}:{peer_port}"
                    peer_nodes[peer_id] = peer_addr
                    logger.info(f"Configured peer: {peer_id} at {peer_addr}")

    # Run the async server
    try:
        asyncio.run(
            run_server(
                node_id,
                ws_host,
                ws_port,
                xmlrpc_host,
                xmlrpc_port,
                xmlrpc_address,
                peer_nodes,
            )
        )
    except KeyboardInterrupt:
        logger.info("Shutting down node server...")
        sys.exit(0)


if __name__ == "__main__":
    main()
