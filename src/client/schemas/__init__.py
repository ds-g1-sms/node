"""
Schemas Package

This package contains protocol message schemas for client-server communication.
Schemas are organized by category: room, member, and message operations.

The package provides base classes (BaseRequest, BaseResponse) that eliminate
code duplication for serialization and deserialization methods.
"""

from .base import BaseRequest, BaseResponse
from .room import (
    CreateRoomRequest,
    RoomCreatedResponse,
    RoomInfo,
    ListRoomsRequest,
    RoomsListResponse,
)
from .member import (
    JoinRoomRequest,
    JoinRoomSuccessResponse,
    JoinRoomErrorResponse,
    MemberJoinedNotification,
)
from .message import (
    SendMessageRequest,
    MessageSentConfirmation,
    NewMessageNotification,
    MessageErrorResponse,
)

__all__ = [
    # Base classes
    "BaseRequest",
    "BaseResponse",
    # Room schemas
    "CreateRoomRequest",
    "RoomCreatedResponse",
    "RoomInfo",
    "ListRoomsRequest",
    "RoomsListResponse",
    # Member schemas
    "JoinRoomRequest",
    "JoinRoomSuccessResponse",
    "JoinRoomErrorResponse",
    "MemberJoinedNotification",
    # Message schemas
    "SendMessageRequest",
    "MessageSentConfirmation",
    "NewMessageNotification",
    "MessageErrorResponse",
]
