"""
Message Buffer for Client-Side Message Ordering

This module provides a buffer for handling out-of-order message delivery
in a distributed chat system. Messages are stored and retrieved in the
correct sequence order as determined by the administrator node.

Architecture:
    - Uses binary search for efficient insertion (O(log n))
    - Maintains sorted order by sequence_number
    - Provides sequential message retrieval (no gaps)
    - Limits buffer size to prevent memory exhaustion

Usage:
    buffer = MessageBuffer()
    buffer.add_message(message_data)
    displayable = buffer.get_new_messages()
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Maximum number of messages to keep in buffer
DEFAULT_MAX_BUFFER_SIZE = 1000

# Maximum number of displayed message IDs to track for deduplication
# This limits memory growth in long-running applications
DEFAULT_MAX_DISPLAYED_IDS = 5000


class MessageBuffer:
    """
    Buffer for ordering messages by sequence number.

    This class maintains a sorted buffer of messages and provides
    methods to retrieve messages in the correct order, handling
    out-of-order delivery gracefully.

    Attributes:
        messages: List of messages sorted by sequence_number
        last_displayed_seq: Last sequence number that was displayed
        max_buffer_size: Maximum number of messages to buffer
    """

    def __init__(
        self,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
        max_displayed_ids: int = DEFAULT_MAX_DISPLAYED_IDS,
    ):
        """
        Initialize the message buffer.

        Args:
            max_buffer_size: Maximum number of messages to keep in buffer.
                             Older messages will be removed when exceeded.
            max_displayed_ids: Maximum number of displayed message IDs to track.
                               Prevents unbounded memory growth.
        """
        self.messages: List[Dict[str, Any]] = []
        self.last_displayed_seq: int = 0
        self.max_buffer_size = max_buffer_size
        self._max_displayed_ids = max_displayed_ids
        self._seen_message_ids: set = set()
        # Track displayed IDs: set for O(1) lookup, list for FIFO order
        self._displayed_message_ids_set: set = set()
        self._displayed_message_ids_list: List[str] = []

    def add_message(self, message: Dict[str, Any]) -> bool:
        """
        Add a message to the buffer in sorted order.

        The message is inserted at the correct position based on its
        sequence_number. Duplicate messages (by message_id) are ignored.

        Args:
            message: Message dictionary containing at least:
                     - sequence_number: int
                     - message_id: str (optional, for deduplication)

        Returns:
            bool: True if message was added, False if duplicate or invalid

        Raises:
            ValueError: If message is missing required fields or invalid
        """
        # Validate message has required fields
        if not isinstance(message, dict):
            logger.warning("Invalid message type: expected dict")
            return False

        sequence_number = message.get("sequence_number")
        if sequence_number is None:
            logger.warning("Message missing sequence_number")
            return False

        # Validate sequence_number is a positive integer
        if not isinstance(sequence_number, int) or sequence_number < 1:
            logger.warning(
                "Invalid sequence_number: %s (must be positive integer)",
                sequence_number,
            )
            return False

        # Check for duplicate by message_id (including already displayed)
        message_id = message.get("message_id")
        if message_id:
            if (
                message_id in self._seen_message_ids
                or message_id in self._displayed_message_ids_set
            ):
                logger.debug("Duplicate message ignored: %s", message_id)
                return False

        # Check for duplicate by sequence_number (already displayed)
        if sequence_number <= self.last_displayed_seq:
            logger.debug(
                "Already displayed sequence_number ignored: %s",
                sequence_number,
            )
            return False

        # Find insert position using binary search
        insert_pos = self._find_insert_position(sequence_number)

        # Check for duplicate by sequence_number using binary search result
        if insert_pos < len(self.messages):
            if (
                self.messages[insert_pos].get("sequence_number")
                == sequence_number
            ):
                logger.debug(
                    "Duplicate sequence_number ignored: %s", sequence_number
                )
                return False

        self.messages.insert(insert_pos, message)

        # Track message_id for deduplication
        if message_id:
            self._seen_message_ids.add(message_id)

        logger.debug(
            "Message added at position %s (seq: %s)",
            insert_pos,
            sequence_number,
        )

        # Enforce buffer size limit
        self._enforce_buffer_limit()

        return True

    def get_new_messages(self) -> List[Dict[str, Any]]:
        """
        Get messages ready to display (sequential from last displayed).

        Returns messages that follow sequentially from the last displayed
        sequence number. Stops at the first gap in sequence numbers.

        Returns:
            List of messages ready to be displayed in order.
            Empty list if no new sequential messages are available.
        """
        displayable: List[Dict[str, Any]] = []
        expected_seq = self.last_displayed_seq + 1

        for msg in self.messages:
            msg_seq = msg.get("sequence_number", 0)
            if msg_seq == expected_seq:
                displayable.append(msg)
                expected_seq += 1
            elif msg_seq > expected_seq:
                # Gap detected - stop here
                break
            # Skip messages with lower sequence than expected
            # (already displayed or invalid)

        if displayable:
            self.last_displayed_seq = displayable[-1]["sequence_number"]
            # Remove displayed messages from buffer
            self.messages = self.messages[len(displayable) :]
            # Move message IDs from seen to displayed for deduplication
            for msg in displayable:
                msg_id = msg.get("message_id")
                if msg_id:
                    self._seen_message_ids.discard(msg_id)
                    self._displayed_message_ids_set.add(msg_id)
                    self._displayed_message_ids_list.append(msg_id)
            # Enforce limit on displayed IDs to prevent unbounded growth
            self._enforce_displayed_ids_limit()

        return displayable

    def has_gap(self) -> bool:
        """
        Check if there are gaps in sequence numbers.

        A gap exists if the first buffered message has a sequence number
        greater than last_displayed_seq + 1.

        Returns:
            True if there is a gap, False otherwise.
        """
        if not self.messages:
            return False
        first_seq = self.messages[0].get("sequence_number", 0)
        return first_seq > self.last_displayed_seq + 1

    def get_missing_sequences(self) -> List[int]:
        """
        Get list of missing sequence numbers.

        Returns the sequence numbers that are expected but not yet
        received, based on the gap between last_displayed_seq and
        the first buffered message.

        Returns:
            List of missing sequence numbers.
        """
        if not self.messages:
            return []

        first_seq = self.messages[0].get("sequence_number", 0)
        expected_start = self.last_displayed_seq + 1

        if first_seq <= expected_start:
            return []

        return list(range(expected_start, first_seq))

    def get_buffered_count(self) -> int:
        """
        Get the number of messages currently buffered.

        Returns:
            Number of messages in the buffer.
        """
        return len(self.messages)

    def clear(self) -> None:
        """
        Clear the buffer and reset state.

        This should be called when leaving a room or disconnecting.
        """
        self.messages.clear()
        self.last_displayed_seq = 0
        self._seen_message_ids.clear()
        self._displayed_message_ids_set.clear()
        self._displayed_message_ids_list.clear()
        logger.debug("Message buffer cleared")

    def set_last_displayed_seq(self, sequence_number: int) -> None:
        """
        Set the last displayed sequence number.

        This can be used when joining a room with existing messages
        to start from a specific sequence.

        Args:
            sequence_number: The sequence number to start from.
        """
        if sequence_number >= 0:
            self.last_displayed_seq = sequence_number
            logger.debug("Last displayed sequence set to %s", sequence_number)

    def _find_insert_position(self, sequence_number: int) -> int:
        """
        Find the correct insert position using binary search.

        Args:
            sequence_number: The sequence number to find position for.

        Returns:
            Index where message should be inserted.
        """
        left, right = 0, len(self.messages)
        while left < right:
            mid = (left + right) // 2
            if self.messages[mid].get("sequence_number", 0) < sequence_number:
                left = mid + 1
            else:
                right = mid
        return left

    def _enforce_buffer_limit(self) -> None:
        """
        Remove oldest messages if buffer exceeds maximum size.

        This prevents memory exhaustion from accumulating too many
        out-of-order messages that may never be displayed.
        """
        if len(self.messages) > self.max_buffer_size:
            excess = len(self.messages) - self.max_buffer_size
            removed = self.messages[:excess]
            self.messages = self.messages[excess:]

            # Clean up seen message IDs for removed messages
            for msg in removed:
                msg_id = msg.get("message_id")
                if msg_id:
                    self._seen_message_ids.discard(msg_id)

            logger.warning(
                "Buffer limit exceeded, removed %s oldest messages", excess
            )

    def _enforce_displayed_ids_limit(self) -> None:
        """
        Remove oldest displayed message IDs if limit is exceeded.

        This prevents unbounded memory growth from tracking too many
        displayed message IDs in long-running applications.
        """
        if len(self._displayed_message_ids_list) > self._max_displayed_ids:
            excess = (
                len(self._displayed_message_ids_list) - self._max_displayed_ids
            )
            # Remove oldest IDs (FIFO)
            for _ in range(excess):
                old_id = self._displayed_message_ids_list.pop(0)
                self._displayed_message_ids_set.discard(old_id)
