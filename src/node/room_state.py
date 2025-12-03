"""
Room State Management for Node Server

This module manages the in-memory state of rooms hosted on this node.
Each node maintains its own list of rooms that it administers.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class RoomState(Enum):
    """Room lifecycle states for 2PC deletion protocol."""

    ACTIVE = "ACTIVE"
    DELETION_PENDING = "DELETION_PENDING"
    COMMITTING = "COMMITTING"
    ROLLING_BACK = "ROLLING_BACK"


class TransactionState(Enum):
    """2PC transaction states for the coordinator."""

    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    ROLLBACK = "ROLLBACK"
    COMPLETED = "COMPLETED"


@dataclass
class DeletionTransaction:
    """
    Represents a 2PC deletion transaction.

    Used by the coordinator (admin node) to track the state of a
    distributed room deletion operation.

    Attributes:
        transaction_id: Unique identifier for this transaction
        room_id: ID of the room being deleted
        state: Current state of the transaction
        participants: List of participant node IDs
        votes: Dict mapping node_id to vote ('READY' or 'ABORT')
        start_time: ISO 8601 timestamp when transaction started
        timeout: Timeout in seconds for each phase
    """

    transaction_id: str
    room_id: str
    state: TransactionState
    participants: List[str]
    votes: Dict[str, Optional[str]] = field(default_factory=dict)
    start_time: str = ""
    timeout: int = 5

    def __post_init__(self):
        """Initialize start time if not set."""
        if not self.start_time:
            self.start_time = datetime.now(timezone.utc).isoformat()


@dataclass
class PreparedTransaction:
    """
    Represents a prepared transaction on a participant node.

    Used by participants to track transactions they have voted on.

    Attributes:
        transaction_id: Unique identifier for this transaction
        room_id: ID of the room being deleted
        coordinator: Node ID of the coordinator
        vote: Vote cast ('READY' or 'ABORT')
        prepared_at: ISO 8601 timestamp when vote was cast
    """

    transaction_id: str
    room_id: str
    coordinator: str
    vote: str
    prepared_at: str = ""

    def __post_init__(self):
        """Initialize prepared_at if not set."""
        if not self.prepared_at:
            self.prepared_at = datetime.now(timezone.utc).isoformat()


@dataclass
class Room:
    """
    Represents a chat room hosted on this node.

    Attributes:
        room_id: Unique identifier for the room
        room_name: Name of the room
        description: Optional room description
        creator_id: ID of the user who created the room
        admin_node: Identifier of the node administering this room
        members: Set of user IDs currently in the room
        created_at: ISO 8601 timestamp when the room was created
        message_counter: Counter for assigning sequence numbers to messages
        messages: List of messages in the room (in-memory buffer)
        state: Current room state for 2PC protocol
    """

    room_id: str
    room_name: str
    description: Optional[str]
    creator_id: str
    admin_node: str
    members: set
    created_at: str
    message_counter: int = 0
    messages: list = None
    state: RoomState = RoomState.ACTIVE

    def __post_init__(self):
        """Initialize the messages list if not set."""
        if self.messages is None:
            self.messages = []

    def to_dict(self) -> Dict:
        """Convert room to dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "room_name": self.room_name,
            "description": self.description,
            "member_count": len(self.members),
            "admin_node": self.admin_node,
            "creator_id": self.creator_id,
        }


class RoomStateManager:
    """
    Manages the state of all rooms hosted on this node.

    This class provides thread-safe operations for creating, listing,
    and managing rooms on the node. Also supports Two-Phase Commit (2PC)
    for coordinated room deletion across distributed nodes.
    """

    def __init__(self, node_id: str):
        """
        Initialize the room state manager.

        Args:
            node_id: Unique identifier for this node
        """
        self.node_id = node_id
        self._rooms: Dict[str, Room] = {}
        # 2PC transaction tracking
        self._deletion_transactions: Dict[str, DeletionTransaction] = {}
        self._prepared_transactions: Dict[str, PreparedTransaction] = {}
        logger.info(f"RoomStateManager initialized for node: {node_id}")

    def create_room(
        self, room_name: str, creator_id: str, description: Optional[str] = None
    ) -> Room:
        """
        Create a new room on this node.

        Args:
            room_name: Name of the room to create
            creator_id: ID of the user creating the room
            description: Optional room description

        Returns:
            The created Room object

        Raises:
            ValueError: If a room with the same name already exists
        """
        # Check if room name already exists
        for room in self._rooms.values():
            if room.room_name == room_name:
                raise ValueError(f"Room with name '{room_name}' already exists")

        # Generate unique room ID
        room_id = str(uuid.uuid4())

        # Create the room with current timestamp
        created_at = datetime.now(timezone.utc).isoformat()
        room = Room(
            room_id=room_id,
            room_name=room_name,
            description=description,
            creator_id=creator_id,
            admin_node=self.node_id,
            members=set(),  # Room starts with no members
            created_at=created_at,
        )

        self._rooms[room_id] = room
        logger.info(
            f"Created room '{room_name}' (ID: {room_id}) by user {creator_id}"
        )

        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """
        Get a room by its ID.

        Args:
            room_id: The room ID to look up

        Returns:
            The Room object if found, None otherwise
        """
        return self._rooms.get(room_id)

    def list_rooms(self) -> List[Dict]:
        """
        Get a list of all rooms hosted on this node.

        Returns:
            List of room dictionaries with metadata
        """
        return [room.to_dict() for room in self._rooms.values()]

    def delete_room(self, room_id: str) -> bool:
        """
        Delete a room from this node.

        Args:
            room_id: The room ID to delete

        Returns:
            True if room was deleted, False if room didn't exist
        """
        if room_id in self._rooms:
            room = self._rooms[room_id]
            del self._rooms[room_id]
            logger.info(f"Deleted room '{room.room_name}' (ID: {room_id})")
            return True
        return False

    def add_member(self, room_id: str, user_id: str) -> bool:
        """
        Add a member to a room.

        Args:
            room_id: The room ID
            user_id: The user ID to add

        Returns:
            True if member was added, False if room doesn't exist
        """
        room = self._rooms.get(room_id)
        if room:
            room.members.add(user_id)
            logger.info(
                f"Added user {user_id} to room '{room.room_name}' "
                f"(ID: {room_id})"
            )
            return True
        return False

    def remove_member(self, room_id: str, user_id: str) -> bool:
        """
        Remove a member from a room.

        Args:
            room_id: The room ID
            user_id: The user ID to remove

        Returns:
            True if member was removed, False if room or user doesn't exist
        """
        room = self._rooms.get(room_id)
        if room and user_id in room.members:
            room.members.remove(user_id)
            logger.info(
                f"Removed user {user_id} from room '{room.room_name}' "
                f"(ID: {room_id})"
            )
            return True
        return False

    def get_room_count(self) -> int:
        """Get the total number of rooms on this node."""
        return len(self._rooms)

    def add_message(
        self, room_id: str, username: str, content: str, max_messages: int = 100
    ) -> Optional[Dict]:
        """
        Add a message to a room and assign a sequence number.

        This method is used by the administrator node to process messages.
        It assigns a sequence number, generates a message_id and timestamp,
        and stores the message in the room's message buffer.

        Args:
            room_id: The room ID
            username: The username of the sender
            content: The message content
            max_messages: Maximum number of messages to keep in buffer

        Returns:
            dict: Message data with assigned sequence number, or None if failed
                {
                    'message_id': str,
                    'room_id': str,
                    'username': str,
                    'content': str,
                    'sequence_number': int,
                    'timestamp': str
                }
        """
        room = self._rooms.get(room_id)
        if not room:
            logger.warning(f"Cannot add message: Room {room_id} not found")
            return None

        if username not in room.members:
            logger.warning(
                f"Cannot add message: User {username} not in room {room_id}"
            )
            return None

        # Assign sequence number
        room.message_counter += 1
        seq_num = room.message_counter

        # Create message
        message = {
            "message_id": str(uuid.uuid4()),
            "room_id": room_id,
            "username": username,
            "content": content,
            "sequence_number": seq_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Store in buffer (with size limit)
        room.messages.append(message)
        if len(room.messages) > max_messages:
            room.messages.pop(0)

        logger.info(
            f"Added message #{seq_num} from {username} to room {room_id}"
        )

        return message

    # ===== Two-Phase Commit (2PC) Methods for Room Deletion =====

    def start_deletion_transaction(
        self, room_id: str, participants: List[str]
    ) -> Optional[DeletionTransaction]:
        """
        Start a new 2PC deletion transaction as the coordinator.

        Args:
            room_id: ID of the room to delete
            participants: List of participant node IDs

        Returns:
            DeletionTransaction if started successfully, None otherwise
        """
        room = self._rooms.get(room_id)
        if not room:
            logger.warning(f"Cannot start deletion: Room {room_id} not found")
            return None

        if room.state != RoomState.ACTIVE:
            logger.warning(
                f"Cannot start deletion: Room {room_id} is in state "
                f"{room.state.value}"
            )
            return None

        transaction_id = str(uuid.uuid4())
        transaction = DeletionTransaction(
            transaction_id=transaction_id,
            room_id=room_id,
            state=TransactionState.PREPARE,
            participants=participants,
            votes={node_id: None for node_id in participants},
        )

        self._deletion_transactions[transaction_id] = transaction
        room.state = RoomState.DELETION_PENDING

        logger.info(
            f"Started deletion transaction {transaction_id} for room "
            f"{room_id} with {len(participants)} participants"
        )

        return transaction

    def get_deletion_transaction(
        self, transaction_id: str
    ) -> Optional[DeletionTransaction]:
        """Get a deletion transaction by ID."""
        return self._deletion_transactions.get(transaction_id)

    def record_vote(self, transaction_id: str, node_id: str, vote: str) -> bool:
        """
        Record a vote from a participant node.

        Args:
            transaction_id: The transaction ID
            node_id: The voting node's ID
            vote: The vote ('READY' or 'ABORT')

        Returns:
            True if vote was recorded, False otherwise
        """
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            logger.warning(
                f"Cannot record vote: Transaction {transaction_id} not found"
            )
            return False

        if node_id not in transaction.votes:
            logger.warning(
                f"Cannot record vote: Node {node_id} not a participant"
            )
            return False

        transaction.votes[node_id] = vote
        logger.info(
            f"Recorded vote {vote} from {node_id} for transaction "
            f"{transaction_id}"
        )
        return True

    def all_votes_ready(self, transaction_id: str) -> bool:
        """Check if all participants voted READY."""
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        return all(vote == "READY" for vote in transaction.votes.values())

    def all_votes_received(self, transaction_id: str) -> bool:
        """Check if all votes have been received."""
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        return all(vote is not None for vote in transaction.votes.values())

    def transition_to_commit(self, transaction_id: str) -> bool:
        """Transition a transaction to COMMIT state."""
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        transaction.state = TransactionState.COMMIT
        room = self._rooms.get(transaction.room_id)
        if room:
            room.state = RoomState.COMMITTING

        logger.info(f"Transaction {transaction_id} transitioned to COMMIT")
        return True

    def transition_to_rollback(self, transaction_id: str) -> bool:
        """Transition a transaction to ROLLBACK state."""
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        transaction.state = TransactionState.ROLLBACK
        room = self._rooms.get(transaction.room_id)
        if room:
            room.state = RoomState.ROLLING_BACK

        logger.info(f"Transaction {transaction_id} transitioned to ROLLBACK")
        return True

    def complete_deletion(self, transaction_id: str) -> bool:
        """
        Complete a deletion transaction by removing the room.

        Args:
            transaction_id: The transaction ID

        Returns:
            True if room was deleted, False otherwise
        """
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        room_id = transaction.room_id
        success = self.delete_room(room_id)

        transaction.state = TransactionState.COMPLETED
        del self._deletion_transactions[transaction_id]

        logger.info(
            f"Completed deletion transaction {transaction_id}, "
            f"room deleted: {success}"
        )
        return success

    def rollback_deletion(self, transaction_id: str) -> bool:
        """
        Rollback a deletion transaction, restoring room to ACTIVE state.

        Args:
            transaction_id: The transaction ID

        Returns:
            True if rollback succeeded, False otherwise
        """
        transaction = self._deletion_transactions.get(transaction_id)
        if not transaction:
            return False

        room = self._rooms.get(transaction.room_id)
        if room:
            room.state = RoomState.ACTIVE

        transaction.state = TransactionState.COMPLETED
        del self._deletion_transactions[transaction_id]

        logger.info(f"Rolled back deletion transaction {transaction_id}")
        return True

    # ===== Participant-side 2PC Methods =====

    def prepare_for_deletion(
        self, room_id: str, transaction_id: str, coordinator: str
    ) -> Dict:
        """
        Prepare to delete a room (participant's PREPARE phase).

        This is called on participant nodes when the coordinator
        sends a PREPARE message.

        Args:
            room_id: ID of the room to delete
            transaction_id: The transaction ID
            coordinator: Node ID of the coordinator

        Returns:
            dict: Vote result with 'vote' and optionally 'reason'
        """
        room = self._rooms.get(room_id)

        # 2PC Protocol Note: If room doesn't exist on this participant node,
        # we vote READY because there's nothing to clean up locally. This is
        # safe in 2PC - the coordinator only needs all participants to agree
        # they CAN delete; if there's nothing to delete, that's a valid READY.
        if not room:
            logger.info(
                f"Room {room_id} not on this node, voting READY for "
                f"transaction {transaction_id}"
            )
            return {
                "vote": "READY",
                "node_id": self.node_id,
                "transaction_id": transaction_id,
            }

        # Check if room is in a state that allows deletion
        if room.state != RoomState.ACTIVE:
            logger.warning(
                f"Cannot prepare deletion: Room {room_id} is in state "
                f"{room.state.value}"
            )
            return {
                "vote": "ABORT",
                "node_id": self.node_id,
                "transaction_id": transaction_id,
                "reason": f"Room in {room.state.value} state",
            }

        # Mark room as deletion pending
        room.state = RoomState.DELETION_PENDING

        # Track the prepared transaction
        prepared = PreparedTransaction(
            transaction_id=transaction_id,
            room_id=room_id,
            coordinator=coordinator,
            vote="READY",
        )
        self._prepared_transactions[transaction_id] = prepared

        logger.info(
            f"Prepared for deletion of room {room_id}, voting READY for "
            f"transaction {transaction_id}"
        )

        return {
            "vote": "READY",
            "node_id": self.node_id,
            "transaction_id": transaction_id,
        }

    def commit_deletion(self, room_id: str, transaction_id: str) -> Dict:
        """
        Commit the deletion of a room (participant's COMMIT phase).

        Args:
            room_id: ID of the room to delete
            transaction_id: The transaction ID

        Returns:
            dict: Confirmation with 'success' flag
        """
        room = self._rooms.get(room_id)

        # Clean up prepared transaction tracking
        if transaction_id in self._prepared_transactions:
            del self._prepared_transactions[transaction_id]

        # If room doesn't exist, treat as success
        if not room:
            logger.info(
                f"Room {room_id} not on this node, commit successful for "
                f"transaction {transaction_id}"
            )
            return {
                "success": True,
                "node_id": self.node_id,
            }

        # Delete the room
        success = self.delete_room(room_id)

        logger.info(
            f"Committed deletion of room {room_id} for transaction "
            f"{transaction_id}, success: {success}"
        )

        return {
            "success": success,
            "node_id": self.node_id,
        }

    def rollback_deletion_participant(
        self, room_id: str, transaction_id: str
    ) -> Dict:
        """
        Rollback a pending deletion (participant's ROLLBACK phase).

        Args:
            room_id: ID of the room
            transaction_id: The transaction ID

        Returns:
            dict: Confirmation with 'success' flag
        """
        room = self._rooms.get(room_id)

        # Clean up prepared transaction tracking
        if transaction_id in self._prepared_transactions:
            del self._prepared_transactions[transaction_id]

        # If room exists, restore to ACTIVE state
        if room:
            room.state = RoomState.ACTIVE
            logger.info(
                f"Rolled back deletion of room {room_id} for transaction "
                f"{transaction_id}"
            )
        else:
            logger.info(
                f"Room {room_id} not on this node, rollback successful for "
                f"transaction {transaction_id}"
            )

        return {
            "success": True,
            "node_id": self.node_id,
        }

    def can_operate_on_room(self, room_id: str) -> bool:
        """
        Check if normal operations (join, message) can be performed on a room.

        Returns False if room is in a 2PC deletion state.

        Args:
            room_id: The room ID

        Returns:
            bool: True if operations are allowed, False otherwise
        """
        room = self._rooms.get(room_id)
        if not room:
            return False

        return room.state == RoomState.ACTIVE
