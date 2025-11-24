#!/usr%bin/env python3
"""
Chat Client Application

Client application for connecting to the distributed chat system.
"""

import logging
import asyncio
import websockets
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

async def list_rooms(uri="ws://localhost:8081"):
    async with websockets.connect(uri) as ws:
        logger.info("Connected to node at %s", uri)
        await ws.send(json.dumps({"type": "list_rooms"}))
        logger.info("Sent list_rooms request")

        response = await ws.recv()

        return json.loads(response)
    
def print_rooms(data):
    print("\n=== Rooms Available ===")
    for room in data["data"]["rooms"]:
        print(f"- {room['room_name']} ({room['member_count']} members)")
    print(f"Total rooms: {data['data']['total_count']}\n")

def main():
    """Main entry point for the chat client."""
    logger.info("Starting chat client...")

    # TODO: Implement client
    # - Connect to node via WebSocket
    # - Join chat room
    # - Send and receive messages
    # - Handle user input

    print("Chat client ready")

    data = asyncio.run(list_rooms())
    print_rooms(data) 

    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Client disconnected")


if __name__ == "__main__":
    main()
