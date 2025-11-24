"""
Node Service for Distributed Chat System

Handles all client → server WebSocket messages.
Supports:
    - create_room

Architecture:
    - Async/await for non-blocking I/O
    - WebSocket for bidirectional real-time communication
"""

import json
import logging
import uuid
from datetime import datetime, UTC

from src.node.state import NodeState

logger = logging.getLogger(__name__)


class NodeService:
    """
    Main node service for handling requests from clients
    """

    def __init__(self, node_id: str, state: NodeState):
        """
        Initialize the client service

        Args:
            node_id: Identifier of the node
            state: State that stores in-memory rooms
        """
        self.node_id = node_id
        self.state = state

        logger.info(f"NodeService initialized for node: {node_id}")

    async def handle_message(self, websocket, message):
        """
        Entry point for handling incoming WebSocket messages
        """
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            await self._send_error(websocket, "invalid_json", "Message must be valid JSON.")
            return

        msg_type = message.get("type")
        data = message.get("data", {})

        if msg_type == "create_room_request":
            await self.handle_create_room(websocket, data)
        else:
            await self._send_error(websocket, "unknown_type", f"Unknown message type '{msg_type}'.")


    async def handle_create_room(self, websocket, data):
        """
        Handles room creation

        Expected request format:
        {
            "type": "create_room_request",
            "data": {
                "room_name": "...",
                "creator_id": "...",
                "description": "..."
            }
        }
        """

        # 1. Validate input
        room_name = data.get("room_name")
        creator_id = data.get("creator_id")
        description = data.get("description", "")

        if not room_name or not isinstance(room_name, str):
            await self._send_error(websocket, "invalid_input", "room_name must be a non-empty string.")
            return

        if not isinstance(creator_id, str) or not creator_id.strip():
            await self._send_error(websocket, "invalid_input", "creator_id must be a non-empty string.")
            return

        # 2. Uniqueness Check
        if self.state.room_exists(room_name):
            await self._send_error(websocket, "duplicate_room", f"Room '{room_name}' already exists.")
            return

        # 3. Create Room
        room_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()

        room_obj = {
            "room_id": room_id,
            "room_name": room_name,
            "description": description,
            "node_id": self.node_id,
            "members": [creator_id],
            "creator_id": creator_id,
            "created_at": created_at,
        }

        # 4. Store Room
        self.state.add_room(room_obj)

        # 5. Send response
        response = {
            "type": "room_created_response",
            "data": {
                "room_id": room_id,
                "room_name": room_name,
                "node_id": self.node_id,
                "success": True,
                "message": None
            },
        }

        await websocket.send(json.dumps(response))

    async def _send_error(self, websocket, code, message):
        """
        Unified error response format
        """
        logger.warning(f"Error {code}: {message}")

        payload = {
            "type": "error",
            "data": {
                "error_code": code,
                "message": message
            }
        }
        await websocket.send(json.dumps(payload))
