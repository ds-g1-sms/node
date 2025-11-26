#!/usr/bin/env python3
"""
Distributed Chat Node Server

A distributed peer-to-peer chat system node server.
"""

import logging
import sys
import asyncio
import os

from .room_state import RoomStateManager
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
        room_manager, xmlrpc_host, xmlrpc_port, xmlrpc_address
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

    # Keep server running
    try:
        # Wait indefinitely
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        # Stop servers
        await ws_server.stop()
        xmlrpc_server.stop()
        logger.info("Node server stopped")


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
