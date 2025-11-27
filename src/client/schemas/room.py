"""
Room Schema Definitions

This module defines the message structures for room-related operations
including room creation, listing, and room information.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseRequest, BaseResponse


@dataclass
class CreateRoomRequest(BaseRequest):
    """
    Request to create a new room on a node.

    Attributes:
        room_name: Name of the room to create
        creator_id: ID of the user creating the room
    """

    room_name: str
    creator_id: str

    @property
    def _message_type(self) -> str:
        """Return the message type for room creation requests."""
        return "create_room"


@dataclass
class RoomCreatedResponse(BaseResponse):
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


@dataclass
class RoomInfo:
    """
    Information about a chat room.

    Note: This is a data transfer object used within RoomsListResponse,
    not a standalone response that needs deserialization methods.
    Room dictionaries are deserialized in RoomsListResponse._from_data().

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
class ListRoomsRequest(BaseRequest):
    """
    Request to list all rooms on a node.

    This is a simple request with no additional parameters.
    The base class to_dict() handles empty requests automatically.
    """

    @property
    def _message_type(self) -> str:
        """Return the message type for list rooms requests."""
        return "list_rooms"


@dataclass
class RoomsListResponse(BaseResponse):
    """
    Response containing a list of rooms.

    Attributes:
        rooms: List of RoomInfo objects
        total_count: Total number of rooms
    """

    rooms: List[RoomInfo]
    total_count: int

    @classmethod
    def _from_data(cls, data: Dict[str, Any]) -> "RoomsListResponse":
        """Create from response data dictionary."""
        rooms_data = data.get("rooms", [])

        # Convert room dictionaries to RoomInfo objects
        rooms = [
            RoomInfo(
                room_id=room_dict["room_id"],
                room_name=room_dict["room_name"],
                description=room_dict.get("description"),
                member_count=room_dict["member_count"],
                admin_node=room_dict["admin_node"],
            )
            for room_dict in rooms_data
        ]

        return cls(
            rooms=rooms,
            total_count=data.get("total_count", len(rooms)),
        )
