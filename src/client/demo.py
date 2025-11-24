#!/usr/bin/env python3
"""
Demo Script for Client Service

This script demonstrates how to use the ClientService to interact with
a node server. It can be run standalone to test the client functionality.

Usage:
    poetry run python -m src.client.demo
    poetry run python -m src.client.demo --node-url ws://localhost:8000
"""

import asyncio
import argparse
import logging

from .service import ClientService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def demo_create_room():
    """
    Demonstrate creating a room using the client service.

    This function shows:
    1. Initializing the ClientService
    2. Connecting to a node (stubbed for now)
    3. Creating a room
    4. Disconnecting from the node
    """
    # Initialize the service
    service = ClientService(node_url="ws://localhost:8000")

    logger.info("=" * 60)
    logger.info("Client Service Demo - Room Creation")
    logger.info("=" * 60)

    # Note: Connection will fail if no server is running
    # This is expected in the stub implementation
    try:
        # Try to connect (will fail without a real server)
        await service.connect()
    except (ConnectionError, OSError) as e:
        logger.warning(f"Could not connect to server (expected): {e}")
        logger.info(
            "Skipping connection - demonstrating stub functionality only"
        )
        # Mark as connected for demo purposes to allow stub operations
        service._connected = True
        # Create a mock websocket object
        service.websocket = object()

    # Create a room (using stub implementation)
    logger.info("\nAttempting to create a room...")
    response = await service.create_room(
        room_name="general", creator_id="user123"
    )

    logger.info("\nRoom Creation Response:")
    logger.info(f"  Success: {response.success}")
    logger.info(f"  Room ID: {response.room_id}")
    logger.info(f"  Room Name: {response.room_name}")
    logger.info(f"  Node ID: {response.node_id}")
    logger.info(f"  Message: {response.message}")

    # Disconnect
    await service.disconnect()

    logger.info("\n" + "=" * 60)
    logger.info("Demo completed successfully!")
    logger.info("=" * 60)


async def demo_multiple_rooms():
    """
    Demonstrate creating multiple rooms.
    """
    service = ClientService(node_url="ws://localhost:8000")

    logger.info("=" * 60)
    logger.info("Client Service Demo - Multiple Rooms")
    logger.info("=" * 60)

    # Mark as connected for demo purposes
    service._connected = True
    service.websocket = object()

    # Create multiple rooms
    rooms = [
        ("general", "user123"),
        ("random", "user123"),
        ("tech-talk", "user456"),
    ]

    for room_name, creator_id in rooms:
        logger.info(f"\nCreating room '{room_name}'...")
        response = await service.create_room(
            room_name=room_name, creator_id=creator_id
        )
        logger.info(f"  -> Created: {response.room_id}")

    logger.info("\n" + "=" * 60)
    logger.info("Multiple rooms demo completed!")
    logger.info("=" * 60)


def main():
    """Main entry point for the demo script."""
    parser = argparse.ArgumentParser(
        description="Demo client service functionality"
    )
    parser.add_argument(
        "--node-url",
        default="ws://localhost:8000",
        help="WebSocket URL of the node server",
    )
    parser.add_argument(
        "--demo",
        choices=["create", "multiple"],
        default="create",
        help="Which demo to run",
    )

    args = parser.parse_args()

    # Run the appropriate demo
    if args.demo == "create":
        asyncio.run(demo_create_room())
    elif args.demo == "multiple":
        asyncio.run(demo_multiple_rooms())


if __name__ == "__main__":
    main()
