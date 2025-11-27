"""
Message Schema Definitions

This module defines the message structures for chat message operations
including sending messages and receiving message notifications.
"""

from dataclasses import dataclass
from typing import Any, Dict

from .base import BaseRequest, BaseResponse


@dataclass
class SendMessageRequest(BaseRequest):
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

    @property
    def _message_type(self) -> str:
        """Return the message type for send message requests."""
        return "send_message"


@dataclass
class MessageSentConfirmation(BaseResponse):
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
    def _from_data(cls, data: Dict[str, Any]) -> "MessageSentConfirmation":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            message_id=data["message_id"],
            sequence_number=data["sequence_number"],
            timestamp=data["timestamp"],
        )


@dataclass
class NewMessageNotification(BaseResponse):
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
    def _from_data(cls, data: Dict[str, Any]) -> "NewMessageNotification":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            message_id=data["message_id"],
            username=data["username"],
            content=data["content"],
            sequence_number=data["sequence_number"],
            timestamp=data["timestamp"],
        )


@dataclass
class MessageErrorResponse(BaseResponse):
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
    def _from_data(cls, data: Dict[str, Any]) -> "MessageErrorResponse":
        """Create from response data dictionary."""
        return cls(
            room_id=data["room_id"],
            error=data["error"],
            error_code=data["error_code"],
        )
