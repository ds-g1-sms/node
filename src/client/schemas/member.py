"""
Member Schema Definitions

This module defines the message structures for room membership operations
including joining, leaving, and member notifications.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseRequest, BaseResponse


@dataclass
class JoinRoomRequest(BaseRequest):
    """
    Request to join an existing room.

    Attributes:
        room_id: ID of the room to join
        username: Username of the joining user
    """

    room_id: str
    username: str

    @property
    def _message_type(self) -> str:
        """Return the message type for join room requests."""
        return "join_room"


@dataclass
class JoinRoomSuccessResponse(BaseResponse):
    """
    Response indicating successful room join.

    Attributes:
        room_id: Unique identifier for the room
        room_name: Name of the room
        description: Optional room description
        members: List of member usernames in the room
        member_count: Number of current members
        admin_node: ID of the node administering this room
    """

    room_id: str
    room_name: str
    description: Optional[str]
    members: List[str]
    member_count: int
    admin_node: str

    @classmethod
    def _from_data(cls, data: Dict[str, Any]) -> "JoinRoomSuccessResponse":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            room_name=data["room_name"],
            description=data.get("description"),
            members=data["members"],
            member_count=data["member_count"],
            admin_node=data["admin_node"],
        )


@dataclass
class JoinRoomErrorResponse(BaseResponse):
    """
    Response indicating failed room join.

    Attributes:
        room_id: ID of the room that was requested
        error: Error message
        error_code: Error code (e.g., ROOM_NOT_FOUND, ALREADY_IN_ROOM)
    """

    room_id: str
    error: str
    error_code: str

    @classmethod
    def _from_data(cls, data: Dict[str, Any]) -> "JoinRoomErrorResponse":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            error=data["error"],
            error_code=data["error_code"],
        )


@dataclass
class MemberJoinedNotification(BaseResponse):
    """
    Notification that a new member joined a room.

    Attributes:
        room_id: ID of the room
        username: Username of the new member
        member_count: Updated member count
        timestamp: ISO 8601 timestamp of the join
    """

    room_id: str
    username: str
    member_count: int
    timestamp: str

    @classmethod
    def _from_data(cls, data: Dict[str, Any]) -> "MemberJoinedNotification":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            username=data["username"],
            member_count=data["member_count"],
            timestamp=data["timestamp"],
        )
