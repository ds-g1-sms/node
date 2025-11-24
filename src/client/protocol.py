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

from typing import Any, Dict, Optional
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
        node_id: ID of the node hosting the room
        success: Whether the operation was successful
        message: Optional message (e.g., error details)
    """

    room_id: str
    room_name: str
    node_id: str
    success: bool = True
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoomCreatedResponse":
        """Create from dictionary."""
        return cls(**data.get("data", data))

    @classmethod
    def from_json(cls, json_str: str) -> "RoomCreatedResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


# TODO: Add more message types as needed:
# - JoinRoomRequest / JoinRoomResponse
# - SendMessageRequest
# - MessageReceivedNotification
# - LeaveRoomRequest
# - RoomListRequest / RoomListResponse
