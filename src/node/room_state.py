"""
Room State Management for Node Server

This module manages the in-memory state of rooms hosted on this node.
Each node maintains its own list of rooms that it administers.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Room:
    """
    Represents a chat room hosted on this node.

    Attributes:
        room_id: Unique identifier for the room
        room_name: Name of the room
        description: Optional room description
        creator_id: ID of the user who created the room
        admin_node: Identifier of the node administering this room
        members: Set of user IDs currently in the room
        created_at: ISO 8601 timestamp when the room was created
        message_counter: Counter for assigning sequence numbers to messages
        messages: List of messages in the room (in-memory buffer)
    """

    room_id: str
    room_name: str
    description: Optional[str]
    creator_id: str
    admin_node: str
    members: set
    created_at: str
    message_counter: int = 0
    messages: list = None

    def __post_init__(self):
        """Initialize the messages list if not set."""
        if self.messages is None:
            self.messages = []

    def to_dict(self) -> Dict:
        """Convert room to dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "description": self.description,
            "member_count": len(self.members),
            "admin_node": self.admin_node,
        }


class RoomStateManager:
    """
    Manages the state of all rooms hosted on this node.

    This class provides thread-safe operations for creating, listing,
    and managing rooms on the node.
    """

    def __init__(self, node_id: str):
        """
        Initialize the room state manager.

        Args:
            node_id: Unique identifier for this node
        """
        self.node_id = node_id
        self._rooms: Dict[str, Room] = {}
        logger.info(f"RoomStateManager initialized for node: {node_id}")

    def create_room(
        self, room_name: str, creator_id: str, description: Optional[str] = None
    ) -> Room:
        """
        Create a new room on this node.

        Args:
            room_name: Name of the room to create
            creator_id: ID of the user creating the room
            description: Optional room description

        Returns:
            The created Room object

        Raises:
            ValueError: If a room with the same name already exists
        """
        # Check if room name already exists
        for room in self._rooms.values():
            if room.room_name == room_name:
                raise ValueError(f"Room with name '{room_name}' already exists")

        # Generate unique room ID
        room_id = str(uuid.uuid4())

        # Create the room with current timestamp
        created_at = datetime.now(timezone.utc).isoformat()
        room = Room(
            room_id=room_id,
            room_name=room_name,
            description=description,
            creator_id=creator_id,
            admin_node=self.node_id,
            members={creator_id},  # Creator is automatically a member
            created_at=created_at,
        )

        self._rooms[room_id] = room
        logger.info(
            f"Created room '{room_name}' (ID: {room_id}) by user {creator_id}"
        )

        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by its ID.

        Args:
            room_id: The room ID to look up

        Returns:
            The Room object if found, None otherwise
        """
        return self._rooms.get(room_id)

    def list_rooms(self) -> List[Dict]:
        """
        Get a list of all rooms hosted on this node.

        Returns:
            List of room dictionaries with metadata
        """
        return [room.to_dict() for room in self._rooms.values()]

    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room from this node.

        Args:
            room_id: The room ID to delete

        Returns:
            True if room was deleted, False if room didn't exist
        """
        if room_id in self._rooms:
            room = self._rooms[room_id]
            del self._rooms[room_id]
            logger.info(f"Deleted room '{room.room_name}' (ID: {room_id})")
            return True
        return False

    def add_member(self, room_id: str, user_id: str) -> bool:
        """
        Add a member to a room.

        Args:
            room_id: The room ID
            user_id: The user ID to add

        Returns:
            True if member was added, False if room doesn't exist
        """
        room = self._rooms.get(room_id)
        if room:
            room.members.add(user_id)
            logger.info(
                f"Added user {user_id} to room '{room.room_name}' "
                f"(ID: {room_id})"
            )
            return True
        return False

    def remove_member(self, room_id: str, user_id: str) -> bool:
        """
        Remove a member from a room.

        Args:
            room_id: The room ID
            user_id: The user ID to remove

        Returns:
            True if member was removed, False if room or user doesn't exist
        """
        room = self._rooms.get(room_id)
        if room and user_id in room.members:
            room.members.remove(user_id)
            logger.info(
                f"Removed user {user_id} from room '{room.room_name}' "
                f"(ID: {room_id})"
            )
            return True
        return False

    def get_room_count(self) -> int:
        """Get the total number of rooms on this node."""
        return len(self._rooms)

    def add_message(
        self, room_id: str, username: str, content: str, max_messages: int = 100
    ) -> Optional[Dict]:
        """
        Add a message to a room and assign a sequence number.

        This method is used by the administrator node to process messages.
        It assigns a sequence number, generates a message_id and timestamp,
        and stores the message in the room's message buffer.

        Args:
            room_id: The room ID
            username: The username of the sender
            content: The message content
            max_messages: Maximum number of messages to keep in buffer

        Returns:
            dict: Message data with assigned sequence number, or None if failed
                {
                    'message_id': str,
                    'room_id': str,
                    'username': str,
                    'content': str,
                    'sequence_number': int,
                    'timestamp': str
                }
        """
        room = self._rooms.get(room_id)
        if not room:
            logger.warning(f"Cannot add message: Room {room_id} not found")
            return None

        if username not in room.members:
            logger.warning(
                f"Cannot add message: User {username} not in room {room_id}"
            )
            return None

        # Assign sequence number
        room.message_counter += 1
        seq_num = room.message_counter

        # Create message
        message = {
            "message_id": str(uuid.uuid4()),
            "room_id": room_id,
            "username": username,
            "content": content,
            "sequence_number": seq_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store in buffer (with size limit)
        room.messages.append(message)
        if len(room.messages) > max_messages:
            room.messages.pop(0)

        logger.info(
            f"Added message #{seq_num} from {username} to room {room_id}"
        )

        return message
