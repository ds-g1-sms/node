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


@dataclass
class JoinRoomRequest:
    """
    Request to join an existing room.

    Attributes:
        room_id: ID of the room to join
        username: Username of the joining user
    """

    room_id: str
    username: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"type": "join_room", "data": asdict(self)}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class JoinRoomSuccessResponse:
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
    def from_dict(cls, data: Dict[str, Any]) -> "JoinRoomSuccessResponse":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            room_name=response_data["room_name"],
            description=response_data.get("description"),
            members=response_data["members"],
            member_count=response_data["member_count"],
            admin_node=response_data["admin_node"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "JoinRoomSuccessResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class JoinRoomErrorResponse:
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
    def from_dict(cls, data: Dict[str, Any]) -> "JoinRoomErrorResponse":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            error=response_data["error"],
            error_code=response_data["error_code"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "JoinRoomErrorResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MemberJoinedNotification:
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
    def from_dict(cls, data: Dict[str, Any]) -> "MemberJoinedNotification":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            username=response_data["username"],
            member_count=response_data["member_count"],
            timestamp=response_data["timestamp"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MemberJoinedNotification":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class SendMessageRequest:
    """
    Request to send a message to a room.

    Attributes:
        room_id: ID of the room to send the message to
        username: Username of the sender
        content: The message content
    """

    room_id: str
    username: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"type": "send_message", "data": asdict(self)}

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class MessageSentConfirmation:
    """
    Confirmation that a message was successfully sent.

    Attributes:
        room_id: ID of the room
        message_id: Unique identifier for the message
        sequence_number: Assigned sequence number for ordering
        timestamp: ISO 8601 timestamp of when message was processed
    """

    room_id: str
    message_id: str
    sequence_number: int
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageSentConfirmation":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            message_id=response_data["message_id"],
            sequence_number=response_data["sequence_number"],
            timestamp=response_data["timestamp"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MessageSentConfirmation":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class NewMessageNotification:
    """
    Notification of a new message in a room.

    Attributes:
        room_id: ID of the room
        message_id: Unique identifier for the message
        username: Username of the sender
        content: The message content
        sequence_number: Sequence number for ordering
        timestamp: ISO 8601 timestamp of when message was processed
    """

    room_id: str
    message_id: str
    username: str
    content: str
    sequence_number: int
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewMessageNotification":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            message_id=response_data["message_id"],
            username=response_data["username"],
            content=response_data["content"],
            sequence_number=response_data["sequence_number"],
            timestamp=response_data["timestamp"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "NewMessageNotification":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class MessageErrorResponse:
    """
    Response indicating failed message send.

    Attributes:
        room_id: ID of the room
        error: Error message
        error_code: Error code (e.g., NOT_MEMBER, INVALID_CONTENT)
    """

    room_id: str
    error: str
    error_code: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageErrorResponse":
        """Create from dictionary."""
        response_data = data.get("data", data)
        return cls(
            room_id=response_data["room_id"],
            error=response_data["error"],
            error_code=response_data["error_code"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MessageErrorResponse":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
