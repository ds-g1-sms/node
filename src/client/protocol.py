"""
Protocol Messages for Client-Server Communication

This module defines the message structures for WebSocket communication
between the client and node servers.

Message Format:
    All messages are JSON objects with the following structure:
    {
        "type": "message_type",
        "data": { ... message-specific data ... }
    }
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class CreateRoomRequest:
    """
    Request to create a new room on a node.

    Attributes:
        room_name: Name of the room to create
        creator_id: ID of the user creating the room
    """

    room_name: str
    creator_id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"type": "create_room", "data": asdict(self)}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class RoomCreatedResponse:
    """
    Response indicating a room was successfully created.

    Attributes:
        room_id: Unique identifier for the created room
        room_name: Name of the room
        admin_node: ID of the node hosting/administering the room
        members: List of member user IDs in the room
        created_at: ISO 8601 timestamp when room was created
    """

    room_id: str
    room_name: str
    admin_node: str
    members: List[str]
    created_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoomCreatedResponse":
        """Create from dictionary."""
        return cls(**data.get("data", data))

    @classmethod
    def from_json(cls, json_str: str) -> "RoomCreatedResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class RoomInfo:
    """
    Information about a chat room.

    Attributes:
        room_id: Unique identifier for the room
        room_name: Name of the room
        description: Optional room description
        member_count: Number of current members in the room
        admin_node: Identifier of the node administering this room
    """

    room_id: str
    room_name: str
    description: Optional[str]
    member_count: int
    admin_node: str


@dataclass
class ListRoomsRequest:
    """
    Request to list all rooms on a node.

    This is a simple request with no additional parameters.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"type": "list_rooms"}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class RoomsListResponse:
    """
    Response containing a list of rooms.

    Attributes:
        rooms: List of RoomInfo objects
        total_count: Total number of rooms
    """

    rooms: List[RoomInfo]
    total_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoomsListResponse":
        """Create from dictionary."""
        response_data = data.get("data", data)
        rooms_data = response_data.get("rooms", [])

        # Convert room dictionaries to RoomInfo objects
        rooms = []
        for room_dict in rooms_data:
            room = RoomInfo(
                room_id=room_dict["room_id"],
                room_name=room_dict["room_name"],
                description=room_dict.get("description"),
                member_count=room_dict["member_count"],
                admin_node=room_dict["admin_node"],
            )
            rooms.append(room)

        return cls(
            rooms=rooms,
            total_count=response_data.get("total_count", len(rooms)),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RoomsListResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


# TODO: Add more message types as needed:
# - JoinRoomRequest / JoinRoomResponse
# - SendMessageRequest
# - MessageReceivedNotification
# - LeaveRoomRequest
