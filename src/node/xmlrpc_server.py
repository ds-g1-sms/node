"""
XML-RPC Server for Inter-Node Communication

Handles XML-RPC requests from peer nodes for distributed operations.
"""

import logging
from datetime import datetime, timezone
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
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
        peer_registry=None,
    ):
        """
        Initialize the XML-RPC server.

        Args:
            room_manager: The room state manager instance
            host: Host address to bind to
            port: Port to listen on
            node_address: Full address of this node (e.g., "http://localhost:9090")
            peer_registry: Optional registry of peer nodes for broadcasting
        """
        self.room_manager = room_manager
        self.host = host
        self.port = port
        self.node_address = node_address
        self.server = None
        self.server_thread = None
        self._broadcast_callback: Optional[Callable] = None
        self.peer_registry = peer_registry

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
        self.server.register_function(self.leave_room, "leave_room")
        self.server.register_function(self.forward_message, "forward_message")
        self.server.register_function(
            self.receive_message_broadcast, "receive_message_broadcast"
        )
        self.server.register_function(
            self.receive_member_event_broadcast,
            "receive_member_event_broadcast",
        )
        # 2PC room deletion methods
        self.server.register_function(
            self.prepare_delete_room, "prepare_delete_room"
        )
        self.server.register_function(
            self.commit_delete_room, "commit_delete_room"
        )
        self.server.register_function(
            self.rollback_delete_room, "rollback_delete_room"
        )

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

        # Check if user is already in the room - allow re-registration
        if username in room.members:
            logger.info(
                f"XML-RPC: User {username} already in room {room_id}, "
                "allowing re-registration"
            )
            # Return success without re-broadcasting join event
            return {
                "success": True,
                "message": "Already in room, re-registered",
                "room_info": {
                    "room_id": room.room_id,
                    "room_name": room.room_name,
                    "description": room.description,
                    "members": list(room.members),
                    "member_count": len(room.members),
                    "admin_node": room.admin_node,
                },
                "messages": room.messages,
            }

        # Add user to the room
        self.room_manager.add_member(room_id, username)

        logger.info(f"XML-RPC: User {username} joined room {room.room_name}")

        # Create member_joined event data
        event_data = {
            "room_id": room_id,
            "username": username,
            "member_count": len(room.members),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Broadcast member_joined to local clients via callback
        if self._broadcast_callback:
            broadcast_msg = {
                "type": "member_joined",
                "data": event_data,
            }
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)

        # Broadcast member_joined to peer nodes via XML-RPC
        if self.peer_registry:
            peers = self.peer_registry.list_peers()
            for peer_node_id, peer_addr in peers.items():
                try:
                    proxy = ServerProxy(peer_addr, allow_none=True)
                    proxy.receive_member_event_broadcast(
                        room_id, "member_joined", event_data
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to broadcast member_joined to {peer_node_id}: {e}"
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
            "messages": room.messages,  # Include existing messages for late joiners
        }

    def forward_message(
        self, room_id: str, username: str, content: str, sender_node_id: str
    ) -> Dict:
        """
        Forward a message to the room administrator for ordering and broadcast.

        This method is exposed via XML-RPC and can be called by peer nodes
        when a client connected to them wants to send a message to a room
        hosted here.

        Args:
            room_id: The ID of the room
            username: The username of the sender
            content: The message content
            sender_node_id: The node the sender is connected to

        Returns:
            dict: Result with structure:
            {
                'success': bool,
                'message_id': str,
                'sequence_number': int,
                'timestamp': str,
                'error': str or None
            }
        """
        logger.info(
            f"XML-RPC: forward_message called for room {room_id} "
            f"from {username} via {sender_node_id}"
        )

        # Validate message content
        if not content:
            return {
                "success": False,
                "error": "Message content cannot be empty",
                "error_code": "INVALID_CONTENT",
            }

        if len(content) > 5000:
            return {
                "success": False,
                "error": "Message content too long (max 5000 characters)",
                "error_code": "INVALID_CONTENT",
            }

        # Get the room
        room = self.room_manager.get_room(room_id)
        if not room:
            logger.warning(f"XML-RPC: Room {room_id} not found")
            return {
                "success": False,
                "error": "Room not found",
                "error_code": "ROOM_NOT_FOUND",
            }

        # Check if user is a member
        if username not in room.members:
            logger.warning(
                f"XML-RPC: User {username} not a member of room {room_id}"
            )
            return {
                "success": False,
                "error": "You are not a member of this room",
                "error_code": "NOT_MEMBER",
            }

        # Add message to room (assigns sequence number)
        message = self.room_manager.add_message(room_id, username, content)

        if not message:
            return {
                "success": False,
                "error": "Failed to add message",
                "error_code": "INTERNAL_ERROR",
            }

        # Broadcast to local clients via callback
        if self._broadcast_callback:
            broadcast_msg = {"type": "new_message", "data": message}
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)

        # Broadcast to peer nodes via XML-RPC
        if self.peer_registry:
            peers = self.peer_registry.list_peers()
            for peer_node_id, peer_addr in peers.items():
                try:
                    proxy = ServerProxy(peer_addr, allow_none=True)
                    proxy.receive_message_broadcast(room_id, message)
                except Exception as e:
                    logger.error(
                        f"Failed to broadcast message to {peer_node_id}: {e}"
                    )

        logger.info(
            f"XML-RPC: Message #{message['sequence_number']} "
            f"from {username} processed"
        )

        return {
            "success": True,
            "message_id": message["message_id"],
            "sequence_number": message["sequence_number"],
            "timestamp": message["timestamp"],
        }

    def receive_message_broadcast(
        self, room_id: str, message_data: Dict
    ) -> bool:
        """
        Receive a message broadcast from the administrator node.

        This method is exposed via XML-RPC and is called by the administrator
        node when it broadcasts a message to all member nodes.

        Args:
            room_id: The ID of the room
            message_data: Message data containing:
                - message_id: str
                - username: str
                - content: str
                - sequence_number: int
                - timestamp: str (ISO format)

        Returns:
            bool: True if successfully delivered to local clients
        """
        logger.info(
            f"XML-RPC: receive_message_broadcast called for room {room_id}, "
            f"msg #{message_data.get('sequence_number')}"
        )

        # Broadcast to local clients via callback
        if self._broadcast_callback:
            broadcast_msg = {"type": "new_message", "data": message_data}
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)
            return True

        logger.warning("No broadcast callback set for message delivery")
        return False

    def receive_member_event_broadcast(
        self, room_id: str, event_type: str, event_data: Dict
    ) -> bool:
        """
        Receive a member event broadcast (join/leave) from the administrator node.

        This method is exposed via XML-RPC and is called by the administrator
        node when it broadcasts member join/leave events to all member nodes.

        Args:
            room_id: The ID of the room
            event_type: Type of event ("member_joined" or "member_left")
            event_data: Event data containing username, member_count, timestamp

        Returns:
            bool: True if successfully delivered to local clients
        """
        logger.info(
            f"XML-RPC: receive_member_event_broadcast called for room {room_id}, "
            f"event {event_type}, user {event_data.get('username')}"
        )

        # Broadcast to local clients via callback
        if self._broadcast_callback:
            broadcast_msg = {"type": event_type, "data": event_data}
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)
            return True

        logger.warning("No broadcast callback set for member event delivery")
        return False

    def leave_room(
        self, room_id: str, username: str, client_node_id: str
    ) -> Dict:
        """
        Handle a leave request for a room administered by this node.

        This method is exposed via XML-RPC and can be called by peer nodes
        when a client connected to them wants to leave a room hosted here.

        Args:
            room_id: The ID of the room to leave
            username: The username of the leaving user
            client_node_id: The node the client is connected to

        Returns:
            dict: Leave result with success status
        """
        logger.info(
            f"XML-RPC: leave_room called for room {room_id} "
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
            }

        # Check if user is in the room
        if username not in room.members:
            logger.warning(f"XML-RPC: User {username} not in room {room_id}")
            return {
                "success": False,
                "message": "Not in room",
                "error_code": "NOT_IN_ROOM",
            }

        # Remove user from the room
        self.room_manager.remove_member(room_id, username)

        logger.info(f"XML-RPC: User {username} left room {room.room_name}")

        # Create member_left event data
        event_data = {
            "room_id": room_id,
            "username": username,
            "member_count": len(room.members),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Broadcast member_left to local clients via callback
        if self._broadcast_callback:
            broadcast_msg = {
                "type": "member_left",
                "data": event_data,
            }
            self._broadcast_callback(room_id, broadcast_msg, exclude_user=None)

        # Broadcast member_left to peer nodes via XML-RPC
        if self.peer_registry:
            peers = self.peer_registry.list_peers()
            for peer_node_id, peer_addr in peers.items():
                try:
                    proxy = ServerProxy(peer_addr, allow_none=True)
                    proxy.receive_member_event_broadcast(
                        room_id, "member_left", event_data
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to broadcast member_left to {peer_node_id}: {e}"
                    )

        return {
            "success": True,
            "message": "Successfully left room",
        }

    # ===== Two-Phase Commit (2PC) Methods for Room Deletion =====

    def prepare_delete_room(
        self, room_id: str, transaction_id: str, coordinator_node: str
    ) -> Dict:
        """
        Phase 1 (PREPARE): Ask participant if ready to delete room.

        This method is exposed via XML-RPC and is called by the coordinator
        node during the PREPARE phase of 2PC.

        Args:
            room_id: ID of room to delete
            transaction_id: Unique transaction identifier
            coordinator_node: Node coordinating the deletion

        Returns:
            dict: Response with structure:
            {
                'vote': 'READY' or 'ABORT',
                'reason': str (if ABORT),
                'node_id': str,
                'transaction_id': str
            }
        """
        logger.info(
            f"XML-RPC: prepare_delete_room called for room {room_id}, "
            f"transaction {transaction_id} from {coordinator_node}"
        )

        result = self.room_manager.prepare_for_deletion(
            room_id, transaction_id, coordinator_node
        )

        return result

    def commit_delete_room(self, room_id: str, transaction_id: str) -> Dict:
        """
        Phase 2 (COMMIT): Instruct participant to delete the room.

        This method is exposed via XML-RPC and is called by the coordinator
        node during the COMMIT phase of 2PC.

        Args:
            room_id: ID of room to delete
            transaction_id: Transaction identifier from PREPARE

        Returns:
            dict: Confirmation with structure:
            {
                'success': bool,
                'node_id': str,
                'error': str or None
            }
        """
        logger.info(
            f"XML-RPC: commit_delete_room called for room {room_id}, "
            f"transaction {transaction_id}"
        )

        # Get room info before deleting for notifications
        room = self.room_manager.get_room(room_id)
        room_name = room.room_name if room else "Unknown"

        result = self.room_manager.commit_deletion(room_id, transaction_id)

        # Notify local clients that room was deleted
        if result.get("success") and self._broadcast_callback:
            notification = {
                "type": "room_deleted",
                "data": {
                    "room_id": room_id,
                    "room_name": room_name,
                    "transaction_id": transaction_id,
                },
            }
            self._broadcast_callback(room_id, notification, exclude_user=None)

        return result

    def rollback_delete_room(self, room_id: str, transaction_id: str) -> Dict:
        """
        Phase 2 (ROLLBACK): Instruct participant to abort deletion.

        This method is exposed via XML-RPC and is called by the coordinator
        node during the ROLLBACK phase of 2PC.

        Args:
            room_id: ID of room
            transaction_id: Transaction identifier from PREPARE

        Returns:
            dict: Confirmation with structure:
            {
                'success': bool,
                'node_id': str
            }
        """
        logger.info(
            f"XML-RPC: rollback_delete_room called for room {room_id}, "
            f"transaction {transaction_id}"
        )

        result = self.room_manager.rollback_deletion_participant(
            room_id, transaction_id
        )

        # Notify local clients that deletion was cancelled
        if result.get("success") and self._broadcast_callback:
            notification = {
                "type": "delete_room_cancelled",
                "data": {
                    "room_id": room_id,
                    "transaction_id": transaction_id,
                },
            }
            self._broadcast_callback(room_id, notification, exclude_user=None)

        return result
