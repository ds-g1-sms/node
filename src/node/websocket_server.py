"""
WebSocket Server for Node

Handles WebSocket connections from clients and processes their requests.
"""

import logging
import json
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

from .room_state import RoomStateManager
from .peer_registry import PeerRegistry

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for handling client connections.

    This server processes incoming WebSocket messages from clients,
    including requests to list rooms, create rooms, join rooms, etc.
    """

    def __init__(
        self,
        room_manager: RoomStateManager,
        host: str,
        port: int,
        peer_registry: PeerRegistry = None,
    ):
        """
        Initialize the WebSocket server.

        Args:
            room_manager: The room state manager instance
            host: Host address to bind to
            port: Port to listen on
            peer_registry: Optional peer registry for distributed operations
        """
        self.room_manager = room_manager
        self.host = host
        self.port = port
        self.peer_registry = peer_registry
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None

    async def start(self):
        """Start the WebSocket server."""
        self.server = await websockets.serve(
            self.handle_client, self.host, self.port
        )
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")

    async def stop(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """
        Handle a client connection.

        Args:
            websocket: The WebSocket connection
        """
        # Register client
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected")

        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Unregister client
            self.clients.discard(websocket)

    async def process_message(
        self, websocket: WebSocketServerProtocol, message: str
    ):
        """
        Process an incoming message from a client.

        Args:
            websocket: The WebSocket connection
            message: The message string (JSON)
        """
        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "list_rooms":
                await self.handle_list_rooms(websocket)
            elif message_type == "create_room":
                await self.handle_create_room(websocket, data)
            elif message_type == "discover_rooms":
                await self.handle_discover_rooms(websocket, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_error(
                    websocket, f"Unknown message type: {message_type}"
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            await self.send_error(websocket, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send_error(websocket, str(e))

    async def handle_list_rooms(self, websocket: WebSocketServerProtocol):
        """
        Handle a list_rooms request.

        Args:
            websocket: The WebSocket connection
        """
        logger.info("Processing list_rooms request")

        # Get all rooms from the room manager
        rooms = self.room_manager.list_rooms()

        # Create response
        response = {
            "type": "rooms_list",
            "data": {"rooms": rooms, "total_count": len(rooms)},
        }

        # Send response
        await websocket.send(json.dumps(response))
        logger.info(f"Sent rooms_list response with {len(rooms)} rooms")

    async def handle_create_room(
        self, websocket: WebSocketServerProtocol, data: dict
    ):
        """
        Handle a create_room request.

        Args:
            websocket: The WebSocket connection
            data: The request data
        """
        try:
            # Extract parameters
            request_data = data.get("data", {})
            room_name = request_data.get("room_name")
            creator_id = request_data.get("creator_id")
            description = request_data.get("description")

            if not room_name or not creator_id:
                raise ValueError("Missing room_name or creator_id")

            logger.info(
                f"Processing create_room request: "
                f"'{room_name}' by {creator_id}"
            )

            # Create the room
            room = self.room_manager.create_room(
                room_name, creator_id, description
            )

            # Create response matching the specification
            response = {
                "type": "room_created",
                "data": {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "admin_node": room.admin_node,
                    "members": list(room.members),
                    "created_at": room.created_at,
                },
            }

            # Send response
            await websocket.send(json.dumps(response))
            logger.info(f"Sent room_created response for room {room.room_id}")

        except ValueError as e:
            logger.error(f"Error creating room: {e}")
            await self.send_error(websocket, str(e), error_type="room_created")
        except Exception as e:
            logger.error(f"Unexpected error creating room: {e}")
            await self.send_error(
                websocket, "Internal server error", error_type="room_created"
            )

    async def handle_discover_rooms(
        self, websocket: WebSocketServerProtocol, data: dict
    ):
        """
        Handle a discover_rooms request for global room discovery.

        Args:
            websocket: The WebSocket connection
            data: The request data
        """
        logger.info("Processing discover_rooms request")

        try:
            # Check if peer registry is available
            if not self.peer_registry:
                # Fall back to local rooms only
                logger.warning(
                    "Peer registry not available, returning local rooms only"
                )
                rooms = self.room_manager.list_rooms()
                response = {
                    "type": "global_rooms_list",
                    "data": {
                        "rooms": rooms,
                        "total_count": len(rooms),
                        "nodes_queried": [self.room_manager.node_id],
                        "nodes_available": [self.room_manager.node_id],
                        "nodes_unavailable": [],
                    },
                }
            else:
                # Get local rooms
                local_rooms = self.room_manager.list_rooms()

                # Discover rooms from all nodes (including peers)
                discovery_result = self.peer_registry.discover_global_rooms(
                    local_rooms
                )

                # Create response
                response = {
                    "type": "global_rooms_list",
                    "data": discovery_result,
                }

            # Send response
            await websocket.send(json.dumps(response))
            logger.info(
                f"Sent global_rooms_list response with "
                f"{response['data']['total_count']} rooms"
            )

        except Exception as e:
            logger.error(f"Error discovering rooms: {e}")
            await self.send_error(
                websocket, "Failed to discover rooms", error_type="error"
            )

    async def send_error(
        self,
        websocket: WebSocketServerProtocol,
        error_message: str,
        error_type: str = "error",
    ):
        """
        Send an error response to a client.

        Args:
            websocket: The WebSocket connection
            error_message: The error message
            error_type: The type of error response
        """
        response = {
            "type": error_type,
            "data": {"success": False, "message": error_message},
        }
        await websocket.send(json.dumps(response))
