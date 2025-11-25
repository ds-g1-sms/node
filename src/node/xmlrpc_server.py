"""
XML-RPC Server for Inter-Node Communication

Handles XML-RPC requests from peer nodes for distributed operations.
"""

import logging
from datetime import datetime, timezone
from xmlrpc.server import SimpleXMLRPCServer
from threading import Thread
from typing import List, Dict, Callable, Optional

from .room_state import RoomStateManager

logger = logging.getLogger(__name__)


class XMLRPCServer:
    """
    XML-RPC server for handling inter-node communication.

    Exposes methods that can be called by peer nodes to coordinate
    distributed operations like room discovery.
    """

    def __init__(
        self,
        room_manager: RoomStateManager,
        host: str,
        port: int,
        node_address: str,
    ):
        """
        Initialize the XML-RPC server.

        Args:
            room_manager: The room state manager instance
            host: Host address to bind to
            port: Port to listen on
            node_address: Full address of this node (e.g., "http://localhost:9090")
        """
        self.room_manager = room_manager
        self.host = host
        self.port = port
        self.node_address = node_address
        self.server = None
        self.server_thread = None
        self._broadcast_callback: Optional[Callable] = None

    def set_broadcast_callback(self, callback: Callable):
        """
        Set a callback for broadcasting messages to room members.

        Args:
            callback: Function that takes (room_id, message_dict) and broadcasts
        """
        self._broadcast_callback = callback

    def start(self):
        """Start the XML-RPC server in a background thread."""
        self.server = SimpleXMLRPCServer(
            (self.host, self.port),
            allow_none=True,
            logRequests=False,
        )

        # Register methods
        self.server.register_function(self.get_hosted_rooms, "get_hosted_rooms")
        self.server.register_function(self.join_room, "join_room")

        logger.info(f"XML-RPC server starting on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"XML-RPC server started at {self.node_address}")

    def _run_server(self):
        """Run the XML-RPC server (called in background thread)."""
        self.server.serve_forever()

    def stop(self):
        """Stop the XML-RPC server."""
        if self.server:
            logger.info("Stopping XML-RPC server")
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=2)
            logger.info("XML-RPC server stopped")

    def get_hosted_rooms(self) -> List[Dict]:
        """
        Returns a list of rooms hosted by this node.

        This method is exposed via XML-RPC and can be called by peer nodes.

        Returns:
            list: List of room dictionaries with structure:
            [
                {
                    'room_id': str,
                    'room_name': str,
                    'description': str,
                    'member_count': int,
                    'admin_node': str,
                    'node_address': str
                },
                ...
            ]
        """
        logger.info("XML-RPC: get_hosted_rooms called")

        # Get rooms from room manager
        rooms = self.room_manager.list_rooms()

        # Add node_address to each room
        for room in rooms:
            room["node_address"] = self.node_address

        logger.info(f"XML-RPC: Returning {len(rooms)} hosted rooms")
        return rooms

    def join_room(
        self, room_id: str, username: str, client_node_id: str
    ) -> Dict:
        """
        Handle a join request for a room administered by this node.

        This method is exposed via XML-RPC and can be called by peer nodes
        when a client connected to them wants to join a room hosted here.

        Args:
            room_id: The ID of the room to join
            username: The username of the joining user
            client_node_id: The node the client is connected to

        Returns:
            dict: Join result with structure:
            {
                'success': bool,
                'message': str,
                'room_info': {
                    'room_id': str,
                    'room_name': str,
                    'description': str,
                    'members': list,
                    'member_count': int,
                    'admin_node': str
                } or None if failed
            }
        """
        logger.info(
            f"XML-RPC: join_room called for room {room_id} "
            f"by {username} from {client_node_id}"
        )

        # Get the room
        room = self.room_manager.get_room(room_id)
        if not room:
            logger.warning(f"XML-RPC: Room {room_id} not found")
            return {
                "success": False,
                "message": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
                "room_info": None,
            }

        # Check if user is already in the room
        if username in room.members:
            logger.warning(
                f"XML-RPC: User {username} already in room {room_id}"
            )
            return {
                "success": False,
                "message": "Already in room",
                "error_code": "ALREADY_IN_ROOM",
                "room_info": None,
            }

        # Add user to the room
        self.room_manager.add_member(room_id, username)

        logger.info(f"XML-RPC: User {username} joined room {room.room_name}")

        # Broadcast member_joined to existing members via callback
        if self._broadcast_callback:
            broadcast_msg = {
                "type": "member_joined",
                "data": {
                    "room_id": room_id,
                    "username": username,
                    "member_count": len(room.members),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)

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
