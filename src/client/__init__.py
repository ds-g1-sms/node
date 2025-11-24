"""
Client Package

This package provides the client-side functionality for the distributed
chat system, including the ClientService for connecting to nodes and
protocol message definitions.
"""

from .service import ClientService
from .protocol import (
    CreateRoomRequest,
    RoomCreatedResponse,
    ListRoomsRequest,
    RoomsListResponse,
    RoomInfo,
)

__all__ = [
    "ClientService",
    "CreateRoomRequest",
    "RoomCreatedResponse",
    "ListRoomsRequest",
    "RoomsListResponse",
    "RoomInfo",
]
