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

import json
import logging
from typing import Optional, Callable
import websockets
from websockets.client import WebSocketClientProtocol

from .protocol import (
    RoomCreatedResponse,
    JoinRoomSuccessResponse,
    JoinRoomRequest,
    SendMessageRequest,
)

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
            - Add timeout handling
            - Add validation for room_name and creator_id
            - Handle node rejection (e.g., duplicate room name)
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info(
            f"Sending create_room request for '{room_name}' by {creator_id}"
        )

        # Import here to avoid issues
        from .protocol import CreateRoomRequest

        # Create and send request
        request = CreateRoomRequest(room_name, creator_id)
        await self.websocket.send(request.to_json())

        # Receive response - loop until we get a create-related response
        # Other messages (like global_rooms_list responses) may be pending
        max_attempts = 10
        for _ in range(max_attempts):
            response_json = await self.websocket.recv()
            response_data = json.loads(response_json)
            response_type = response_data.get("type")

            # Check response type
            if response_type == "room_created":
                response = RoomCreatedResponse.from_json(response_json)
                logger.info(f"Received room_created response: {response}")
                return response
            elif response_type == "room_creation_error":
                error_data = response_data.get("data", {})
                error_msg = error_data.get("error", "Unknown error")
                logger.error(f"Failed to create room: {error_msg}")
                raise ValueError(error_msg)
            else:
                # Skip non-create responses (e.g., pending room list responses)
                logger.debug(
                    f"Skipping non-create response while creating: {response_type}"
                )

        logger.error("Timed out waiting for create room response")
        raise ValueError("Timed out waiting for create room response")

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

    def _set_test_mode(self, mock_websocket: object = None) -> None:
        """
        Set the service in test mode with a mock connection.

        This is a helper method for testing that allows bypassing
        actual WebSocket connections.

        Args:
            mock_websocket: Required mock websocket object with send/recv

        Note: This should only be used in tests or demos.

        Raises:
            ValueError: If mock_websocket is not provided
        """
        if mock_websocket is None:
            raise ValueError("_set_test_mode requires a mock_websocket object")
        self._connected = True
        self.websocket = mock_websocket

    async def list_rooms(self):
        """
        Request a list of all rooms on the connected node.

        Returns:
            RoomsListResponse containing list of rooms and metadata

        Raises:
            ConnectionError: If not connected to a node

        TODO:
            - Add timeout handling
            - Handle node errors gracefully
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info("Sending list_rooms request")

        # Import here to avoid circular dependency issues
        from .protocol import ListRoomsRequest, RoomsListResponse

        # Create and send request
        request = ListRoomsRequest()
        await self.websocket.send(request.to_json())

        # Receive response
        response_json = await self.websocket.recv()
        response = RoomsListResponse.from_json(response_json)

        logger.info(
            f"Received rooms_list response with "
            f"{response.total_count} rooms"
        )
        return response

    async def join_room(
        self, room_id: str, username: str
    ) -> JoinRoomSuccessResponse:
        """
        Send a request to join an existing room.

        Args:
            room_id: ID of the room to join
            username: Username of the user joining the room

        Returns:
            JoinRoomSuccessResponse with room details

        Raises:
            ConnectionError: If not connected to a node server
            ValueError: If join fails (room not found, already in room, etc.)

        TODO:
            - Add timeout handling
            - Add validation for room_id and username
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info(f"Sending join_room request for room '{room_id}'")

        # Create and send request
        request = JoinRoomRequest(room_id, username)
        await self.websocket.send(request.to_json())

        # Receive response - loop until we get a join-related response
        # Other messages (like member_left broadcasts) may be pending
        max_attempts = 10
        for _ in range(max_attempts):
            response_json = await self.websocket.recv()
            response_data = json.loads(response_json)
            response_type = response_data.get("type")

            # Check response type
            if response_type == "join_room_success":
                response = JoinRoomSuccessResponse.from_json(response_json)
                logger.info(f"Successfully joined room '{response.room_name}'")
                return response
            elif response_type == "join_room_error":
                error_data = response_data.get("data", {})
                error_msg = error_data.get("error", "Unknown error")
                logger.error(f"Failed to join room: {error_msg}")
                raise ValueError(error_msg)
            else:
                # Skip non-join responses (e.g., pending broadcasts)
                logger.debug(
                    f"Skipping non-join response while joining: {response_type}"
                )

        logger.error("Timed out waiting for join response")
        raise ValueError("Timed out waiting for join response")

    async def send_message(
        self, room_id: str, username: str, content: str
    ) -> None:
        """
        Send a message to a room.

        This is a fire-and-forget operation. The message confirmation will
        come through the message receive loop asynchronously.

        Args:
            room_id: ID of the room to send the message to
            username: Username of the sender
            content: The message content

        Raises:
            ConnectionError: If not connected to a node server
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info(f"Sending message to room '{room_id}'")

        # Create and send request (fire-and-forget)
        request = SendMessageRequest(room_id, username, content)
        await self.websocket.send(request.to_json())

    async def leave_room(self, room_id: str, username: str) -> None:
        """
        Leave a room.

        This is a fire-and-forget operation. The confirmation will
        come through the message receive loop asynchronously.

        Args:
            room_id: ID of the room to leave
            username: Username of the user leaving

        Raises:
            ConnectionError: If not connected to a node server
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info(f"Leaving room '{room_id}'")

        # Create and send request (fire-and-forget)
        request = json.dumps(
            {
                "type": "leave_room",
                "data": {
                    "room_id": room_id,
                    "username": username,
                },
            }
        )
        await self.websocket.send(request)
