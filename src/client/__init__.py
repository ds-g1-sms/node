"""
Client Package

This package provides the client-side functionality for the distributed
chat system, including the ClientService for connecting to nodes,
protocol message definitions, and the terminal user interface.

Schemas are organized in the `schemas` subpackage by category:
    - room: Room creation, listing, and information
    - member: Room membership operations
    - message: Chat message operations
"""

from .service import ClientService
from .message_buffer import MessageBuffer
from .chat_client import ChatClient
from .schemas import (
    # Base classes
    BaseRequest,
    BaseResponse,
    BaseErrorResponse,
    # Room schemas
    CreateRoomRequest,
    RoomCreatedResponse,
    ListRoomsRequest,
    RoomsListResponse,
    RoomInfo,
    # Member schemas
    JoinRoomRequest,
    JoinRoomSuccessResponse,
    JoinRoomErrorResponse,
    MemberJoinedNotification,
    # Message schemas
    SendMessageRequest,
    MessageSentConfirmation,
    NewMessageNotification,
    MessageErrorResponse,
)

__all__ = [
    # Service classes
    "ClientService",
    "MessageBuffer",
    "ChatClient",
    # Base schema classes
    "BaseRequest",
    "BaseResponse",
    "BaseErrorResponse",
    # Room schemas
    "CreateRoomRequest",
    "RoomCreatedResponse",
    "ListRoomsRequest",
    "RoomsListResponse",
    "RoomInfo",
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
