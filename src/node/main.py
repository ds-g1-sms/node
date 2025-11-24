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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def run_server(node_id: str, host: str, port: int):
    """
    Run the node server with WebSocket support.

    Args:
        node_id: Unique identifier for this node
        host: Host address to bind to
        port: Port to listen on
    """
    # Initialize room state manager
    room_manager = RoomStateManager(node_id)

    # Initialize WebSocket server
    ws_server = WebSocketServer(room_manager, host, port)

    # Start the WebSocket server
    await ws_server.start()

    logger.info(f"Node server '{node_id}' is ready")
    logger.info(f"WebSocket server listening on ws://{host}:{port}")

    # Keep server running
    try:
        # Wait indefinitely
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        # Stop the WebSocket server
        await ws_server.stop()
        logger.info("Node server stopped")


def main():
    """Main entry point for the node server."""
    logger.info("Starting distributed chat node server...")

    # Get configuration from environment or use defaults
    node_id = os.environ.get("NODE_ID", "node1")
    host = os.environ.get("NODE_HOST", "localhost")
    port = int(os.environ.get("NODE_PORT", "8000"))

    # Run the async server
    try:
        asyncio.run(run_server(node_id, host, port))
    except KeyboardInterrupt:
        logger.info("Shutting down node server...")
        sys.exit(0)


if __name__ == "__main__":
    main()
