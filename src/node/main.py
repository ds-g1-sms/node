#!/usr/bin/env python3
"""
Distributed Chat Node Server

A distributed peer-to-peer chat system node server.
"""

import logging
import sys
import asyncio
import websockets
import json
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

rooms = {}

async def handle_client(ws):
    logger.info("Client connected")
    
    try:
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "list_rooms":
                response = {
                    "type": "rooms_list",
                    "data": {
                        "rooms": list(rooms.values()),
                        "total_count": len(rooms),
                    },
                }
                await ws.send(json.dumps(response))
                logger.info("Sent rooms list to client")
        await ws.wait_closed()
        logger.info("Client disconnected")

    except Exception as e:
        logger.error(f"Connection error: {e}")


async def main():
    """Main entry point for the node server."""
    logger.info("Starting distributed chat node server...")

    # TODO: Initialize server components
    # - XML-RPC server for inter-node communication
    # - WebSocket server for client connections
    # - State management
    # - Room management
    # - Node discovery

    print("Node server is ready")

    # TODO: Keep server running
    server = await websockets.serve(handle_client, "0.0.0.0", 8081)
    logger.info("WebSocket server running on ws://localhost:8081")

    try:
        await server.wait_closed()  # Wait indefinitely
    except asyncio.CancelledError:
        # Happens on shutdown — suppress to avoid stacktrace
        pass
    finally:
        logger.info("Shutting down node server...")
        print("Node disconnected")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Clean console message for Ctrl+C
        print("\nNode disconnected")
        logger.info("Node stopped manually via KeyboardInterrupt.")