"""
Client Service for Distributed Chat System

This module provides the main client service class that handles communication
with node servers via WebSocket connections. It manages room operations like
creating rooms, joining rooms, and sending messages.

Architecture:
    - Uses WebSocket for real-time bidirectional communication
    - Supports dependency injection for the network layer (for testability)
    - Async/await pattern for non-blocking I/O operations

Future Enhancements:
    - Connection pooling for multiple nodes
    - Automatic reconnection on failure
    - Message queueing and retry logic
    - Room state caching
"""

import logging
from typing import Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol

from .protocol import RoomCreatedResponse  # noqa: F401

# CreateRoomRequest will be used when full implementation is done

logger = logging.getLogger(__name__)


class ClientService:
    """
    Main client service for interacting with node servers.

    This class provides the entry point for all client-side operations,
    including room creation, joining, and messaging.

    Attributes:
        node_url: WebSocket URL of the node server (e.g., ws://localhost:8000)
        websocket: Active WebSocket connection (None if not connected)
        _message_handler: Optional callback for handling incoming messages
    """

    def __init__(
        self,
        node_url: str,
        websocket_factory: Optional[Callable] = None,
    ):
        """
        Initialize the client service.

        Args:
            node_url: WebSocket URL of the node server
            websocket_factory: Optional factory for creating WebSocket
                             connections (for dependency injection/testing)
        """
        self.node_url = node_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self._websocket_factory = websocket_factory or websockets.connect
        self._message_handler: Optional[Callable[[str], None]] = None
        self._connected = False

        logger.info(f"ClientService initialized for node: {node_url}")

    async def connect(self) -> None:
        """
        Establish WebSocket connection to the node server.

        Raises:
            ConnectionError: If connection fails

        TODO:
            - Add retry logic with exponential backoff
            - Add connection timeout configuration
            - Handle SSL/TLS for secure connections
        """
        try:
            logger.info(f"Connecting to {self.node_url}...")
            self.websocket = await self._websocket_factory(self.node_url)
            self._connected = True
            logger.info("Successfully connected to node server")
        except Exception as e:
            logger.error(f"Failed to connect to node: {e}")
            raise ConnectionError(f"Could not connect to {self.node_url}: {e}")

    async def disconnect(self) -> None:
        """
        Close the WebSocket connection.

        TODO:
            - Send graceful disconnect message to server
            - Clean up any pending operations
        """
        if self.websocket:
            # Only close if it's a real WebSocket connection
            if hasattr(self.websocket, "close"):
                await self.websocket.close()
            self.websocket = None
            self._connected = False
            logger.info("Disconnected from node server")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to a node."""
        return self._connected and self.websocket is not None

    async def create_room(
        self, room_name: str, creator_id: str
    ) -> RoomCreatedResponse:
        """
        Send a request to create a new room on the node.

        Args:
            room_name: Name of the room to create
            creator_id: ID of the user creating the room

        Returns:
            RoomCreatedResponse with room details

        Raises:
            ConnectionError: If not connected to a node
            ValueError: If response is invalid

        TODO:
            - Implement full request/response cycle
            - Add timeout handling
            - Add validation for room_name and creator_id
            - Handle node rejection (e.g., duplicate room name)
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        # Create the request message
        # Note: request object is prepared but not sent in stub implementation
        # request = CreateRoomRequest(
        #     room_name=room_name, creator_id=creator_id
        # )

        logger.info(
            f"Sending create_room request for '{room_name}' by {creator_id}"
        )

        # TODO: Implement actual WebSocket send/receive
        # For now, this is a stub that returns a mock response
        # Real implementation would:
        # 1. await self.websocket.send(request.to_json())
        # 2. response_json = await self.websocket.recv()
        # 3. response = RoomCreatedResponse.from_json(response_json)
        # 4. return response

        # Stub response for development
        stub_response = RoomCreatedResponse(
            room_id=f"room_{room_name}_{creator_id}",
            room_name=room_name,
            node_id="node_stub_001",
            success=True,
            message="Room creation stubbed - not yet implemented",
        )

        logger.info(f"Received room_created response: {stub_response}")
        return stub_response

    async def handle_messages(self) -> None:
        """
        Listen for incoming messages from the server.

        This method runs in a loop receiving messages until the connection
        is closed. Incoming messages are dispatched to the message handler
        if one is registered.

        TODO:
            - Implement message routing based on message type
            - Add error handling for malformed messages
            - Add heartbeat/ping-pong for connection health
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info("Starting message handler loop")

        try:
            async for message in self.websocket:
                logger.debug(f"Received message: {message}")
                if self._message_handler:
                    self._message_handler(message)
                # TODO: Parse message and dispatch to appropriate handler
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
            self._connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            raise

    def set_message_handler(self, handler: Callable[[str], None]) -> None:
        """
        Register a callback for handling incoming messages.

        Args:
            handler: Callback function that receives message strings

        TODO:
            - Support typed message handlers (based on message type)
            - Support multiple handlers for different message types
        """
        self._message_handler = handler

    # TODO: Future methods to implement:
    # - async def join_room(
    #       self, room_id: str, user_id: str
    #   ) -> JoinRoomResponse
    # - async def leave_room(
    #       self, room_id: str, user_id: str
    #   ) -> bool
    # - async def send_message(
    #       self, room_id: str, message: str, user_id: str
    #   ) -> bool
    # - async def list_rooms(self) -> List[RoomInfo]
    # - async def get_room_info(self, room_id: str) -> RoomInfo
