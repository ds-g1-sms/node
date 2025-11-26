"""
WebSocket Server for Node

Handles WebSocket connections from clients and processes their requests.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Set, Dict, Optional
from xmlrpc.client import ServerProxy
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
        # Track which clients are in which rooms
        # Maps room_id -> set of (websocket, username) tuples
        self._room_clients: Dict[str, Set[tuple]] = {}
        # Maps websocket -> set of room_ids
        self._client_rooms: Dict[WebSocketServerProtocol, Set[str]] = {}

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

    def register_client_room_membership(
        self, websocket: WebSocketServerProtocol, room_id: str, username: str
    ):
        """
        Track that a client is a member of a room.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            username: The username of the client
        """
        if room_id not in self._room_clients:
            self._room_clients[room_id] = set()
        self._room_clients[room_id].add((websocket, username))

        if websocket not in self._client_rooms:
            self._client_rooms[websocket] = set()
        self._client_rooms[websocket].add(room_id)

    def unregister_client_room_membership(
        self, websocket: WebSocketServerProtocol, room_id: str = None
    ):
        """
        Remove a client from room membership tracking.

        Args:
            websocket: The WebSocket connection
            room_id: Optional specific room ID to leave. If None, leaves all.
        """
        if room_id:
            # Remove from specific room
            if room_id in self._room_clients:
                self._room_clients[room_id] = {
                    (ws, user)
                    for ws, user in self._room_clients[room_id]
                    if ws != websocket
                }
            if websocket in self._client_rooms:
                self._client_rooms[websocket].discard(room_id)
        else:
            # Remove from all rooms
            if websocket in self._client_rooms:
                for rid in self._client_rooms[websocket]:
                    if rid in self._room_clients:
                        self._room_clients[rid] = {
                            (ws, user)
                            for ws, user in self._room_clients[rid]
                            if ws != websocket
                        }
                del self._client_rooms[websocket]

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict,
        exclude_websocket: Optional[WebSocketServerProtocol] = None,
    ):
        """
        Broadcast a message to all clients in a room.

        Args:
            room_id: The room ID
            message: The message to broadcast
            exclude_websocket: Optional websocket to exclude from broadcast
        """
        if room_id not in self._room_clients:
            return

        message_json = json.dumps(message)
        for websocket, _ in self._room_clients[room_id]:
            if websocket != exclude_websocket:
                try:
                    await websocket.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    pass

    def broadcast_to_room_sync(
        self,
        room_id: str,
        message: dict,
        exclude_user: Optional[str] = None,
    ):
        """
        Synchronous version of broadcast for use in XML-RPC callbacks.
        This schedules the actual broadcast to run in the event loop.

        Args:
            room_id: The room ID
            message: The message to broadcast
            exclude_user: Optional username to exclude from broadcast
        """

        async def _do_broadcast():
            if room_id not in self._room_clients:
                return
            message_json = json.dumps(message)
            for websocket, username in self._room_clients[room_id]:
                if username != exclude_user:
                    try:
                        await websocket.send(message_json)
                    except websockets.exceptions.ConnectionClosed:
                        pass

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_do_broadcast())
            else:
                loop.run_until_complete(_do_broadcast())
        except RuntimeError:
            # No event loop running, create new one
            asyncio.run(_do_broadcast())

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
            # Unregister client from rooms
            self.unregister_client_room_membership(websocket)
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
            elif message_type == "join_room":
                await self.handle_join_room(websocket, data)
            elif message_type == "leave_room":
                await self.handle_leave_room(websocket, data)
            elif message_type == "send_message":
                await self.handle_send_message(websocket, data)
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

    async def handle_join_room(
        self, websocket: WebSocketServerProtocol, data: dict
    ):
        """
        Handle a join_room request.

        Args:
            websocket: The WebSocket connection
            data: The request data
        """
        try:
            # Extract parameters
            request_data = data.get("data", {})
            room_id = request_data.get("room_id")
            username = request_data.get("username")

            if not room_id or not username:
                await self.send_join_error(
                    websocket,
                    room_id or "",
                    "Missing room_id or username",
                    "INVALID_REQUEST",
                )
                return

            logger.info(
                f"Processing join_room request: "
                f"room {room_id} by {username}"
            )

            # Check if this node administers the room
            room = self.room_manager.get_room(room_id)

            if room:
                # Local join - this node is the administrator
                result = await self._handle_local_join(
                    websocket, room_id, username
                )
            else:
                # Try remote join - find the administrator node
                result = await self._handle_remote_join(
                    websocket, room_id, username
                )

            if result["success"]:
                # Track that this client is in the room
                self.register_client_room_membership(
                    websocket, room_id, username
                )

                # Send success response
                response = {
                    "type": "join_room_success",
                    "data": result["room_info"],
                }
                await websocket.send(json.dumps(response))
                logger.info(
                    f"User {username} successfully joined room {room_id}"
                )

                # Send existing messages to the joining user
                # First try local room (for local joins)
                room = self.room_manager.get_room(room_id)
                messages = room.messages if room else []
                # For remote joins, messages are included in the result
                if not messages and "messages" in result:
                    messages = result["messages"]

                if messages:
                    for message in messages:
                        msg_response = {
                            "type": "new_message",
                            "data": message,
                        }
                        await websocket.send(json.dumps(msg_response))
                    logger.info(
                        f"Sent {len(messages)} existing messages "
                        f"to {username}"
                    )
            else:
                await self.send_join_error(
                    websocket,
                    room_id,
                    result["message"],
                    result.get("error_code", "UNKNOWN_ERROR"),
                )

        except Exception as e:
            logger.error(f"Error processing join_room: {e}")
            room_id = data.get("data", {}).get("room_id", "")
            await self.send_join_error(
                websocket, room_id, str(e), "INTERNAL_ERROR"
            )

    async def _handle_local_join(
        self, websocket: WebSocketServerProtocol, room_id: str, username: str
    ) -> dict:
        """
        Handle a join request for a room administered by this node.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            username: The username

        Returns:
            dict: Result with success status and room_info or error
        """
        room = self.room_manager.get_room(room_id)
        if not room:
            return {
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Check if user is already in the room
        already_member = username in room.members

        if not already_member:
            # Add user to the room
            self.room_manager.add_member(room_id, username)

            # Broadcast member_joined to existing members
            broadcast_msg = {
                "type": "member_joined",
                "data": {
                    "room_id": room_id,
                    "username": username,
                    "member_count": len(room.members),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            await self.broadcast_to_room(room_id, broadcast_msg, websocket)
            logger.info(f"User {username} joined local room {room.room_name}")
        else:
            # User is already a member (e.g., room creator)
            # Just log it - we'll register their WebSocket connection below
            logger.info(
                f"User {username} re-joining room {room.room_name} "
                f"(already a member)"
            )

        return {
            "success": True,
            "message": "Successfully joined room",
            "room_info": {
                "room_id": room.room_id,
                "room_name": room.room_name,
                "description": room.description,
                "members": list(room.members),
                "member_count": len(room.members),
                "admin_node": room.admin_node,
            },
        }

    async def _handle_remote_join(
        self, websocket: WebSocketServerProtocol, room_id: str, username: str
    ) -> dict:
        """
        Handle a join request for a room administered by another node.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            username: The username

        Returns:
            dict: Result with success status and room_info or error
        """
        if not self.peer_registry:
            return {
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Try to find the room on peer nodes
        # First, discover all rooms to find which node hosts this room
        local_rooms = self.room_manager.list_rooms()
        discovery_result = self.peer_registry.discover_global_rooms(local_rooms)

        # Find the room in the discovered rooms
        target_room = None
        for room in discovery_result.get("rooms", []):
            if room.get("room_id") == room_id:
                target_room = room
                break

        if not target_room:
            return {
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Get the admin node address
        admin_node = target_room.get("admin_node")
        node_address = target_room.get("node_address")

        if not node_address:
            # Try to get address from peer registry
            node_address = self.peer_registry.get_peer_address(admin_node)

        if not node_address:
            return {
                "success": False,
                "message": "Administrator node unavailable",
                "error_code": "ADMIN_NODE_UNAVAILABLE",
            }

        # Call XML-RPC on the administrator node
        try:
            proxy = ServerProxy(node_address, allow_none=True)
            result = proxy.join_room(
                room_id, username, self.room_manager.node_id
            )

            return result

        except Exception as e:
            logger.error(f"Failed to join remote room: {e}")
            return {
                "success": False,
                "message": f"Failed to contact administrator node: {e}",
                "error_code": "ADMIN_NODE_UNAVAILABLE",
            }

    async def send_join_error(
        self,
        websocket: WebSocketServerProtocol,
        room_id: str,
        error: str,
        error_code: str,
    ):
        """
        Send a join_room error response.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            error: The error message
            error_code: The error code
        """
        response = {
            "type": "join_room_error",
            "data": {
                "room_id": room_id,
                "error": error,
                "error_code": error_code,
            },
        }
        await websocket.send(json.dumps(response))

    async def handle_leave_room(
        self, websocket: WebSocketServerProtocol, data: dict
    ):
        """
        Handle a leave_room request.

        Args:
            websocket: The WebSocket connection
            data: The request data
        """
        try:
            # Extract parameters
            request_data = data.get("data", {})
            room_id = request_data.get("room_id")
            username = request_data.get("username")

            if not room_id or not username:
                await self.send_error(websocket, "Missing room_id or username")
                return

            logger.info(
                f"Processing leave_room request: "
                f"room {room_id} by {username}"
            )

            # Remove client from room membership tracking
            self.unregister_client_room_membership(websocket, room_id)

            # Remove member from room state
            room = self.room_manager.get_room(room_id)
            if room:
                self.room_manager.remove_member(room_id, username)

                # Broadcast member_left to remaining members
                broadcast_msg = {
                    "type": "member_left",
                    "data": {
                        "room_id": room_id,
                        "username": username,
                        "member_count": len(room.members),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
                await self.broadcast_to_room(room_id, broadcast_msg, websocket)

            # Send success response
            response = {
                "type": "leave_room_success",
                "data": {
                    "room_id": room_id,
                    "username": username,
                },
            }
            await websocket.send(json.dumps(response))
            logger.info(f"User {username} left room {room_id}")

        except Exception as e:
            logger.error(f"Error processing leave_room: {e}")
            await self.send_error(websocket, str(e))

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

    async def handle_send_message(
        self, websocket: WebSocketServerProtocol, data: dict
    ):
        """
        Handle a send_message request from a client.

        Args:
            websocket: The WebSocket connection
            data: The request data
        """
        try:
            # Extract parameters
            request_data = data.get("data", {})
            room_id = request_data.get("room_id")
            username = request_data.get("username")
            content = request_data.get("content")

            # Validate required fields
            if not room_id or not username:
                await self.send_message_error(
                    websocket,
                    room_id or "",
                    "Missing room_id or username",
                    "INVALID_REQUEST",
                )
                return

            # Validate message content
            if not content:
                await self.send_message_error(
                    websocket,
                    room_id,
                    "Message content cannot be empty",
                    "INVALID_CONTENT",
                )
                return

            if len(content) > 5000:
                await self.send_message_error(
                    websocket,
                    room_id,
                    "Message content too long (max 5000 characters)",
                    "INVALID_CONTENT",
                )
                return

            logger.info(
                f"Processing send_message request: "
                f"room {room_id} from {username}"
            )

            # Check if user is member of the room (local check)
            if not self._is_client_in_room(websocket, room_id):
                await self.send_message_error(
                    websocket,
                    room_id,
                    "You are not a member of this room",
                    "NOT_MEMBER",
                )
                return

            # Check if this node administers the room
            room = self.room_manager.get_room(room_id)

            if room:
                # Local message - this node is the administrator
                result = await self._handle_local_message(
                    websocket, room_id, username, content
                )
            else:
                # Remote message - forward to administrator
                result = await self._handle_remote_message(
                    websocket, room_id, username, content
                )

            if result["success"]:
                # Send confirmation to sender
                confirmation = {
                    "type": "message_sent",
                    "data": {
                        "room_id": room_id,
                        "message_id": result["message_id"],
                        "sequence_number": result["sequence_number"],
                        "timestamp": result["timestamp"],
                    },
                }
                await websocket.send(json.dumps(confirmation))
                logger.info(
                    f"Message from {username} sent successfully "
                    f"(seq: {result['sequence_number']})"
                )
            else:
                await self.send_message_error(
                    websocket,
                    room_id,
                    result.get("error", "Failed to send message"),
                    result.get("error_code", "UNKNOWN_ERROR"),
                )

        except Exception as e:
            logger.error(f"Error processing send_message: {e}")
            room_id = data.get("data", {}).get("room_id", "")
            await self.send_message_error(
                websocket, room_id, str(e), "INTERNAL_ERROR"
            )

    def _is_client_in_room(
        self, websocket: WebSocketServerProtocol, room_id: str
    ) -> bool:
        """
        Check if a client's websocket is registered as being in a room.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID

        Returns:
            bool: True if client is in the room
        """
        if websocket not in self._client_rooms:
            return False
        return room_id in self._client_rooms[websocket]

    async def _handle_local_message(
        self,
        websocket: WebSocketServerProtocol,
        room_id: str,
        username: str,
        content: str,
    ) -> dict:
        """
        Handle a message for a room administered by this node.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            username: The username
            content: The message content

        Returns:
            dict: Result with success status and message data or error
        """
        # Add message to room (assigns sequence number)
        message = self.room_manager.add_message(room_id, username, content)

        if not message:
            return {
                "success": False,
                "error": "Failed to add message",
                "error_code": "INTERNAL_ERROR",
            }

        # Broadcast to all room members (including sender)
        await self._broadcast_message_to_room(room_id, message)

        return {
            "success": True,
            "message_id": message["message_id"],
            "sequence_number": message["sequence_number"],
            "timestamp": message["timestamp"],
        }

    async def _handle_remote_message(
        self,
        websocket: WebSocketServerProtocol,
        room_id: str,
        username: str,
        content: str,
    ) -> dict:
        """
        Handle a message for a room administered by another node.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            username: The username
            content: The message content

        Returns:
            dict: Result with success status and message data or error
        """
        if not self.peer_registry:
            return {
                "success": False,
                "error": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Find the administrator node for this room
        local_rooms = self.room_manager.list_rooms()
        discovery_result = self.peer_registry.discover_global_rooms(local_rooms)

        # Find the room in the discovered rooms
        target_room = None
        for room in discovery_result.get("rooms", []):
            if room.get("room_id") == room_id:
                target_room = room
                break

        if not target_room:
            return {
                "success": False,
                "error": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Get the admin node address
        admin_node = target_room.get("admin_node")
        node_address = target_room.get("node_address")

        if not node_address:
            node_address = self.peer_registry.get_peer_address(admin_node)

        if not node_address:
            return {
                "success": False,
                "error": "Administrator node unavailable",
                "error_code": "ADMIN_NODE_UNAVAILABLE",
            }

        # Forward message to administrator via XML-RPC
        try:
            proxy = ServerProxy(node_address, allow_none=True)
            result = proxy.forward_message(
                room_id, username, content, self.room_manager.node_id
            )
            return result
        except Exception as e:
            logger.error(f"Failed to forward message: {e}")
            return {
                "success": False,
                "error": f"Failed to contact administrator node: {e}",
                "error_code": "ADMIN_NODE_UNAVAILABLE",
            }

    async def _broadcast_message_to_room(self, room_id: str, message: dict):
        """
        Broadcast a message to all room members.

        For local clients, sends via WebSocket.
        For remote nodes with members in the room, calls XML-RPC.

        Args:
            room_id: The room ID
            message: The message data dict
        """
        # Broadcast to local clients via WebSocket
        broadcast_msg = {"type": "new_message", "data": message}

        if room_id in self._room_clients:
            message_json = json.dumps(broadcast_msg)
            for ws, _ in self._room_clients[room_id]:
                try:
                    await ws.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    pass

        # Broadcast to remote nodes via XML-RPC
        if self.peer_registry:
            peers = self.peer_registry.list_peers()
            for node_id, node_addr in peers.items():
                try:
                    proxy = ServerProxy(node_addr, allow_none=True)
                    proxy.receive_message_broadcast(room_id, message)
                except Exception as e:
                    logger.error(
                        f"Failed to broadcast message to {node_id}: {e}"
                    )

    def broadcast_message_to_room_sync(self, room_id: str, message: dict):
        """
        Synchronous version of broadcast for use in XML-RPC callbacks.

        Args:
            room_id: The room ID
            message: The message data dict
        """
        broadcast_msg = {"type": "new_message", "data": message}

        async def _do_broadcast():
            if room_id not in self._room_clients:
                return
            message_json = json.dumps(broadcast_msg)
            for websocket, _ in self._room_clients[room_id]:
                try:
                    await websocket.send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_do_broadcast())
        except RuntimeError:
            # No running event loop, use asyncio.run
            asyncio.run(_do_broadcast())

    async def send_message_error(
        self,
        websocket: WebSocketServerProtocol,
        room_id: str,
        error: str,
        error_code: str,
    ):
        """
        Send a message_error response.

        Args:
            websocket: The WebSocket connection
            room_id: The room ID
            error: The error message
            error_code: The error code
        """
        response = {
            "type": "message_error",
            "data": {
                "room_id": room_id,
                "error": error,
                "error_code": error_code,
            },
        }
        await websocket.send(json.dumps(response))
