"""
Chat Client for Message Ordering and Handling

This module provides a ChatClient class that extends the base ClientService
with message ordering capabilities. It handles incoming messages from
WebSocket connections, buffers them for ordering, and provides callbacks
for UI integration.

Architecture:
    - Extends ClientService for basic WebSocket operations
    - Uses MessageBuffer for ordering messages by sequence number
    - Provides callback hooks for UI layer integration
    - Handles multiple rooms with separate message buffers

Usage:
    client = ChatClient("ws://localhost:8000")
    await client.connect()
    await client.join_room("room-id", "username")
    await client.receive_messages()
"""

import json
import logging
from typing import Any, Callable, Dict, Optional
import websockets

from .service import ClientService
from .message_buffer import MessageBuffer

logger = logging.getLogger(__name__)


class ChatClient(ClientService):
    """
    Chat client with message ordering capabilities.

    This class extends ClientService with:
    - Per-room message buffers for ordering
    - Callbacks for UI integration
    - Out-of-order message handling
    - Duplicate message detection

    Attributes:
        message_buffers: Dict mapping room_id to MessageBuffer
        username: Current username
        current_room: ID of the currently joined room
        on_message_ready: Callback for messages ready to display
        on_ordering_gap_detected: Callback when gap is detected
        on_duplicate_message: Callback when duplicate is detected
        on_member_joined: Callback when a member joins
    """

    def __init__(
        self,
        node_url: str,
        websocket_factory: Optional[Callable] = None,
    ):
        """
        Initialize the chat client.

        Args:
            node_url: WebSocket URL of the node server
            websocket_factory: Optional factory for creating WebSocket
                             connections (for dependency injection/testing)
        """
        super().__init__(node_url, websocket_factory)

        self.message_buffers: Dict[str, MessageBuffer] = {}
        self.username: Optional[str] = None
        self.current_room: Optional[str] = None

        # Callbacks for UI integration
        self._on_message_ready: Optional[Callable[[Dict[str, Any]], None]] = (
            None
        )
        self._on_ordering_gap_detected: Optional[Callable[[str], None]] = None
        self._on_duplicate_message: Optional[Callable[[str], None]] = None
        self._on_member_joined: Optional[Callable[[Dict[str, Any]], None]] = (
            None
        )
        self._on_member_left: Optional[Callable[[Dict[str, Any]], None]] = None
        # Room deletion callbacks
        self._on_delete_initiated: Optional[
            Callable[[Dict[str, Any]], None]
        ] = None
        self._on_delete_success: Optional[Callable[[Dict[str, Any]], None]] = (
            None
        )
        self._on_delete_failed: Optional[Callable[[Dict[str, Any]], None]] = (
            None
        )
        self._on_room_deleted: Optional[Callable[[Dict[str, Any]], None]] = None

        logger.info("ChatClient initialized for node: %s", node_url)

    def set_username(self, username: str) -> None:
        """
        Set the username for this client.

        Args:
            username: The username to use
        """
        self.username = username
        logger.info("Username set to: %s", username)

    def set_current_room(self, room_id: str) -> None:
        """
        Set the current room ID.

        Args:
            room_id: The room ID to set as current
        """
        self.current_room = room_id
        # Ensure buffer exists for this room
        if room_id not in self.message_buffers:
            self.message_buffers[room_id] = MessageBuffer()
        logger.info("Current room set to: %s", room_id)

    def leave_current_room(self) -> None:
        """
        Leave the current room and clean up.

        Clears the message buffer for the current room.
        """
        if self.current_room:
            if self.current_room in self.message_buffers:
                self.message_buffers[self.current_room].clear()
            logger.info("Left room: %s", self.current_room)
            self.current_room = None

    def set_on_message_ready(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for messages ready to display.

        Args:
            callback: Function that receives message dict when ready
        """
        self._on_message_ready = callback

    def set_on_ordering_gap_detected(
        self, callback: Callable[[str], None]
    ) -> None:
        """
        Register callback for ordering gap detection.

        Args:
            callback: Function that receives room_id when gap detected
        """
        self._on_ordering_gap_detected = callback

    def set_on_duplicate_message(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for duplicate message detection.

        Args:
            callback: Function that receives message_id when duplicate
        """
        self._on_duplicate_message = callback

    def set_on_member_joined(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for member joined notifications.

        Args:
            callback: Function that receives member info dict
        """
        self._on_member_joined = callback

    def set_on_member_left(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for member left notifications.

        Args:
            callback: Function that receives member info dict
        """
        self._on_member_left = callback

    def set_on_delete_initiated(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for when room deletion is initiated.

        Args:
            callback: Function that receives deletion info dict
        """
        self._on_delete_initiated = callback

    def set_on_delete_success(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for successful room deletion.

        Args:
            callback: Function that receives deletion result dict
        """
        self._on_delete_success = callback

    def set_on_delete_failed(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for failed room deletion.

        Args:
            callback: Function that receives failure info dict
        """
        self._on_delete_failed = callback

    def set_on_room_deleted(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register callback for when a room is deleted (notification to members).

        Args:
            callback: Function that receives room deletion info dict
        """
        self._on_room_deleted = callback

    async def receive_messages(self) -> None:
        """
        Continuously receive and process messages from the server.

        This method runs in a loop, receiving messages via WebSocket
        and dispatching them to appropriate handlers based on message type.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to a node server")

        logger.info("Starting message receive loop")

        try:
            async for message in self.websocket:
                await self._process_incoming_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
            self._connected = False
        except Exception as e:
            logger.error("Error in message receive loop: %s", e)
            raise

    async def _process_incoming_message(self, message: str) -> None:
        """
        Process a single incoming message.

        Parses the message and dispatches to appropriate handler.

        Args:
            message: Raw JSON message string from WebSocket
        """
        try:
            data = json.loads(message)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse message JSON: %s", e)
            return

        message_type = data.get("type")

        if message_type == "new_message":
            await self._handle_new_message(data.get("data", {}))
        elif message_type == "member_joined":
            await self._handle_member_joined(data.get("data", {}))
        elif message_type == "member_left":
            await self._handle_member_left(data.get("data", {}))
        elif message_type == "message_sent":
            # Message confirmation - just log it
            logger.debug("Message sent confirmation received")
        elif message_type == "message_error":
            # Message error - log it and notify
            error_data = data.get("data", {})
            error_msg = error_data.get("error", "Unknown error")
            logger.error("Message send error: %s", error_msg)
        elif message_type == "delete_room_initiated":
            await self._handle_delete_initiated(data.get("data", {}))
        elif message_type == "delete_room_success":
            await self._handle_delete_success(data.get("data", {}))
        elif message_type == "delete_room_failed":
            await self._handle_delete_failed(data.get("data", {}))
        elif message_type == "room_deleted":
            await self._handle_room_deleted(data.get("data", {}))
        else:
            # Pass through to the original message handler if registered
            if self._message_handler:
                self._message_handler(message)
            logger.debug("Unhandled message type: %s", message_type)

    async def _handle_new_message(self, message_data: Dict[str, Any]) -> None:
        """
        Handle incoming new_message notification.

        Adds the message to the buffer and processes any messages
        that are ready to display in order.

        Args:
            message_data: Message data dictionary containing:
                - room_id
                - message_id
                - username
                - content
                - sequence_number
                - timestamp
        """
        room_id = message_data.get("room_id")

        # Validate required fields
        if not room_id:
            logger.warning("New message missing room_id")
            return

        # Only process if we're in this room
        if room_id != self.current_room:
            logger.debug(
                "Ignoring message for room %s (current: %s)",
                room_id,
                self.current_room,
            )
            return

        # Get or create message buffer for this room
        if room_id not in self.message_buffers:
            self.message_buffers[room_id] = MessageBuffer()

        buffer = self.message_buffers[room_id]

        # Try to add message to buffer
        added = buffer.add_message(message_data)

        if not added:
            # Message was a duplicate or invalid
            message_id = message_data.get("message_id", "unknown")
            if self._on_duplicate_message:
                self._on_duplicate_message(message_id)
            return

        # Get messages ready to display
        displayable = buffer.get_new_messages()

        # Notify for each message ready to display
        for msg in displayable:
            if self._on_message_ready:
                self._on_message_ready(msg)

        # Check for gaps
        if buffer.has_gap():
            if self._on_ordering_gap_detected:
                self._on_ordering_gap_detected(room_id)

    async def _handle_member_joined(self, member_data: Dict[str, Any]) -> None:
        """
        Handle member_joined notification.

        Args:
            member_data: Member data dictionary containing:
                - room_id
                - username
                - member_count
                - timestamp
        """
        room_id = member_data.get("room_id")

        # Only notify if we're in this room
        if room_id != self.current_room:
            return

        if self._on_member_joined:
            self._on_member_joined(member_data)

        logger.info(
            "Member %s joined room %s",
            member_data.get("username"),
            room_id,
        )

    async def _handle_member_left(self, member_data: Dict[str, Any]) -> None:
        """
        Handle member_left notification.

        Args:
            member_data: Member data dictionary containing:
                - room_id
                - username
                - member_count
                - timestamp
        """
        room_id = member_data.get("room_id")

        # Only notify if we're in this room
        if room_id != self.current_room:
            return

        if self._on_member_left:
            self._on_member_left(member_data)

        logger.info(
            "Member %s left room %s",
            member_data.get("username"),
            room_id,
        )

    async def _handle_delete_initiated(
        self, delete_data: Dict[str, Any]
    ) -> None:
        """
        Handle delete_room_initiated notification.

        Args:
            delete_data: Deletion data dictionary containing:
                - room_id
                - initiator (optional)
                - transaction_id
                - status
        """
        room_id = delete_data.get("room_id")
        logger.info(
            "Room deletion initiated for room %s",
            room_id,
        )

        if self._on_delete_initiated:
            self._on_delete_initiated(delete_data)

    async def _handle_delete_success(self, delete_data: Dict[str, Any]) -> None:
        """
        Handle delete_room_success notification.

        Args:
            delete_data: Deletion result dictionary containing:
                - room_id
                - transaction_id
                - message
        """
        room_id = delete_data.get("room_id")
        logger.info(
            "Room deletion successful for room %s",
            room_id,
        )

        if self._on_delete_success:
            self._on_delete_success(delete_data)

    async def _handle_delete_failed(self, delete_data: Dict[str, Any]) -> None:
        """
        Handle delete_room_failed notification.

        Args:
            delete_data: Failure info dictionary containing:
                - room_id
                - reason
                - error_code
                - transaction_id (optional)
        """
        room_id = delete_data.get("room_id")
        reason = delete_data.get("reason", "Unknown reason")
        logger.error(
            "Room deletion failed for room %s: %s",
            room_id,
            reason,
        )

        if self._on_delete_failed:
            self._on_delete_failed(delete_data)

    async def _handle_room_deleted(self, delete_data: Dict[str, Any]) -> None:
        """
        Handle room_deleted notification (for members of a deleted room).

        Args:
            delete_data: Room deletion info dictionary containing:
                - room_id
                - room_name
                - message
        """
        room_id = delete_data.get("room_id")
        room_name = delete_data.get("room_name", "Unknown")
        logger.info(
            "Room '%s' (ID: %s) has been deleted",
            room_name,
            room_id,
        )

        # Clear message buffer for the deleted room
        if room_id in self.message_buffers:
            self.message_buffers[room_id].clear()
            del self.message_buffers[room_id]

        # If we were in this room, clear current room
        if self.current_room == room_id:
            self.current_room = None

        if self._on_room_deleted:
            self._on_room_deleted(delete_data)

    def get_buffer_for_room(self, room_id: str) -> Optional[MessageBuffer]:
        """
        Get the message buffer for a specific room.

        Args:
            room_id: The room ID

        Returns:
            MessageBuffer for the room, or None if not found
        """
        return self.message_buffers.get(room_id)

    def get_buffered_message_count(self, room_id: Optional[str] = None) -> int:
        """
        Get the number of buffered messages for a room.

        Args:
            room_id: Room ID, or None for current room

        Returns:
            Number of buffered messages
        """
        target_room = room_id or self.current_room
        if not target_room:
            return 0

        buffer = self.message_buffers.get(target_room)
        if not buffer:
            return 0

        return buffer.get_buffered_count()
