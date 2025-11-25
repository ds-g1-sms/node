"""
Tests for Message Ordering Functionality

Tests for the MessageBuffer and ChatClient classes that handle
out-of-order message delivery in the distributed chat system.
"""

import json
import pytest

from src.client import MessageBuffer, ChatClient


# MessageBuffer Tests


class TestMessageBufferBasics:
    """Basic tests for MessageBuffer functionality."""

    def test_message_buffer_can_be_created(self):
        """Test that MessageBuffer can be instantiated."""
        buffer = MessageBuffer()
        assert buffer is not None
        assert buffer.last_displayed_seq == 0
        assert buffer.messages == []

    def test_message_buffer_with_custom_size(self):
        """Test MessageBuffer with custom max size."""
        buffer = MessageBuffer(max_buffer_size=50)
        assert buffer.max_buffer_size == 50

    def test_add_single_message(self):
        """Test adding a single message to the buffer."""
        buffer = MessageBuffer()
        message = {
            "message_id": "msg-1",
            "username": "alice",
            "content": "Hello!",
            "sequence_number": 1,
            "timestamp": "2025-11-23T10:00:00Z",
        }
        result = buffer.add_message(message)
        assert result is True
        assert buffer.get_buffered_count() == 1

    def test_add_message_validates_sequence_number(self):
        """Test that add_message validates sequence_number."""
        buffer = MessageBuffer()

        # Missing sequence_number
        result = buffer.add_message({"message_id": "msg-1"})
        assert result is False

        # Invalid sequence_number (not positive int)
        result = buffer.add_message(
            {"message_id": "msg-2", "sequence_number": 0}
        )
        assert result is False

        result = buffer.add_message(
            {"message_id": "msg-3", "sequence_number": -1}
        )
        assert result is False

        result = buffer.add_message(
            {"message_id": "msg-4", "sequence_number": "1"}
        )
        assert result is False

    def test_add_message_validates_input_type(self):
        """Test that add_message validates input type."""
        buffer = MessageBuffer()

        # Invalid input type
        result = buffer.add_message("not a dict")
        assert result is False

        result = buffer.add_message(None)
        assert result is False


class TestMessageBufferOrdering:
    """Tests for message ordering in MessageBuffer."""

    def test_messages_in_order(self):
        """Test messages arriving in order are immediately displayable."""
        buffer = MessageBuffer()

        for i in range(1, 5):
            buffer.add_message(
                {"message_id": f"msg-{i}", "sequence_number": i}
            )

        displayable = buffer.get_new_messages()
        assert len(displayable) == 4
        assert buffer.last_displayed_seq == 4
        assert [m["sequence_number"] for m in displayable] == [1, 2, 3, 4]

    def test_messages_out_of_order(self):
        """Test messages arriving out of order."""
        buffer = MessageBuffer()

        # Message 1 arrives first
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 1
        assert buffer.last_displayed_seq == 1

        # Message 3 arrives (skip 2)
        buffer.add_message({"message_id": "msg-3", "sequence_number": 3})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 0  # Gap detected

        # Message 2 arrives
        buffer.add_message({"message_id": "msg-2", "sequence_number": 2})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 2
        assert [m["sequence_number"] for m in displayable] == [2, 3]
        assert buffer.last_displayed_seq == 3

        # Message 4 arrives
        buffer.add_message({"message_id": "msg-4", "sequence_number": 4})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 1
        assert buffer.last_displayed_seq == 4

    def test_reverse_order_messages(self):
        """Test messages arriving in reverse order."""
        buffer = MessageBuffer()

        # Messages arrive in reverse order: 4, 3, 2, 1
        buffer.add_message({"message_id": "msg-4", "sequence_number": 4})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 0

        buffer.add_message({"message_id": "msg-3", "sequence_number": 3})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 0

        buffer.add_message({"message_id": "msg-2", "sequence_number": 2})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 0

        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 4
        assert [m["sequence_number"] for m in displayable] == [1, 2, 3, 4]

    def test_sorted_insertion(self):
        """Test that messages are inserted in sorted order."""
        buffer = MessageBuffer()

        buffer.add_message({"message_id": "msg-3", "sequence_number": 3})
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        buffer.add_message({"message_id": "msg-4", "sequence_number": 4})
        buffer.add_message({"message_id": "msg-2", "sequence_number": 2})

        # Check internal ordering
        sequences = [m["sequence_number"] for m in buffer.messages]
        assert sequences == [1, 2, 3, 4]


class TestMessageBufferGapDetection:
    """Tests for gap detection in MessageBuffer."""

    def test_has_gap_no_messages(self):
        """Test has_gap with empty buffer."""
        buffer = MessageBuffer()
        assert buffer.has_gap() is False

    def test_has_gap_sequential(self):
        """Test has_gap with sequential messages."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        assert buffer.has_gap() is False

    def test_has_gap_with_missing(self):
        """Test has_gap when first message creates gap."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-2", "sequence_number": 2})
        assert buffer.has_gap() is True

    def test_has_gap_after_display(self):
        """Test has_gap after some messages displayed."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        buffer.add_message({"message_id": "msg-3", "sequence_number": 3})

        # Display message 1
        buffer.get_new_messages()
        assert buffer.last_displayed_seq == 1

        # Should detect gap (missing 2)
        assert buffer.has_gap() is True

    def test_get_missing_sequences(self):
        """Test get_missing_sequences returns correct missing numbers."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        buffer.get_new_messages()

        buffer.add_message({"message_id": "msg-5", "sequence_number": 5})

        missing = buffer.get_missing_sequences()
        assert missing == [2, 3, 4]


class TestMessageBufferDuplicates:
    """Tests for duplicate handling in MessageBuffer."""

    def test_duplicate_message_id_ignored(self):
        """Test that duplicate message_ids are ignored."""
        buffer = MessageBuffer()

        msg1 = {"message_id": "msg-1", "sequence_number": 1}
        result1 = buffer.add_message(msg1)
        assert result1 is True

        # Same message_id
        msg2 = {"message_id": "msg-1", "sequence_number": 1}
        result2 = buffer.add_message(msg2)
        assert result2 is False
        assert buffer.get_buffered_count() == 1

    def test_duplicate_sequence_number_ignored(self):
        """Test that duplicate sequence_numbers are ignored."""
        buffer = MessageBuffer()

        msg1 = {"message_id": "msg-1", "sequence_number": 1}
        buffer.add_message(msg1)

        # Different message_id but same sequence
        msg2 = {"message_id": "msg-2", "sequence_number": 1}
        result = buffer.add_message(msg2)
        assert result is False
        assert buffer.get_buffered_count() == 1


class TestMessageBufferLimit:
    """Tests for buffer size limit in MessageBuffer."""

    def test_buffer_size_limit(self):
        """Test that buffer respects size limit."""
        buffer = MessageBuffer(max_buffer_size=10)

        # Add more messages than the limit
        for i in range(1, 16):
            buffer.add_message(
                {"message_id": f"msg-{i}", "sequence_number": i}
            )

        assert buffer.get_buffered_count() == 10
        # Oldest should be removed
        assert buffer.messages[0]["sequence_number"] == 6

    def test_buffer_clear(self):
        """Test buffer clear functionality."""
        buffer = MessageBuffer()
        for i in range(1, 5):
            buffer.add_message(
                {"message_id": f"msg-{i}", "sequence_number": i}
            )
        buffer.get_new_messages()

        buffer.clear()

        assert buffer.messages == []
        assert buffer.last_displayed_seq == 0
        assert buffer.get_buffered_count() == 0


class TestMessageBufferEdgeCases:
    """Edge case tests for MessageBuffer."""

    def test_first_message_sequence_one(self):
        """Test that first message with sequence 1 works correctly."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        displayable = buffer.get_new_messages()
        assert len(displayable) == 1
        assert displayable[0]["sequence_number"] == 1

    def test_large_gap(self):
        """Test handling of large gaps in sequence numbers."""
        buffer = MessageBuffer()
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})
        buffer.get_new_messages()

        # Large gap
        buffer.add_message(
            {"message_id": "msg-100", "sequence_number": 100}
        )

        assert buffer.has_gap() is True
        missing = buffer.get_missing_sequences()
        assert len(missing) == 98
        assert missing[0] == 2
        assert missing[-1] == 99

    def test_set_last_displayed_seq(self):
        """Test setting last_displayed_seq manually."""
        buffer = MessageBuffer()
        buffer.set_last_displayed_seq(10)
        assert buffer.last_displayed_seq == 10

        # Add message after the last displayed
        buffer.add_message(
            {"message_id": "msg-11", "sequence_number": 11}
        )
        displayable = buffer.get_new_messages()
        assert len(displayable) == 1

    def test_message_without_message_id(self):
        """Test message without message_id is still accepted."""
        buffer = MessageBuffer()
        msg = {"sequence_number": 1, "content": "Hello"}
        result = buffer.add_message(msg)
        assert result is True
        assert buffer.get_buffered_count() == 1


# ChatClient Tests


class TestChatClientBasics:
    """Basic tests for ChatClient functionality."""

    def test_chat_client_can_be_created(self):
        """Test that ChatClient can be instantiated."""
        client = ChatClient(node_url="ws://localhost:8000")
        assert client is not None
        assert client.node_url == "ws://localhost:8000"
        assert not client.is_connected
        assert client.message_buffers == {}
        assert client.username is None
        assert client.current_room is None

    def test_set_username(self):
        """Test setting username."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_username("alice")
        assert client.username == "alice"

    def test_set_current_room(self):
        """Test setting current room creates buffer."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")
        assert client.current_room == "room-123"
        assert "room-123" in client.message_buffers

    def test_leave_current_room(self):
        """Test leaving current room clears buffer."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        # Add some messages
        buffer = client.message_buffers["room-123"]
        buffer.add_message({"message_id": "msg-1", "sequence_number": 1})

        client.leave_current_room()

        assert client.current_room is None
        assert client.message_buffers["room-123"].get_buffered_count() == 0


class TestChatClientCallbacks:
    """Tests for ChatClient callback functionality."""

    def test_set_callbacks(self):
        """Test setting callbacks."""
        client = ChatClient(node_url="ws://localhost:8000")

        received = []

        def on_message(msg):
            received.append(("message", msg))

        def on_gap(room_id):
            received.append(("gap", room_id))

        def on_duplicate(msg_id):
            received.append(("duplicate", msg_id))

        def on_member(member):
            received.append(("member", member))

        client.set_on_message_ready(on_message)
        client.set_on_ordering_gap_detected(on_gap)
        client.set_on_duplicate_message(on_duplicate)
        client.set_on_member_joined(on_member)

        assert client._on_message_ready is not None
        assert client._on_ordering_gap_detected is not None
        assert client._on_duplicate_message is not None
        assert client._on_member_joined is not None


class TestChatClientMessageHandling:
    """Tests for ChatClient message handling."""

    @pytest.mark.asyncio
    async def test_handle_new_message_in_order(self):
        """Test handling messages arriving in order."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received_messages = []
        client.set_on_message_ready(
            lambda msg: received_messages.append(msg)
        )

        # Process messages
        for i in range(1, 4):
            await client._handle_new_message({
                "room_id": "room-123",
                "message_id": f"msg-{i}",
                "username": "alice",
                "content": f"Message {i}",
                "sequence_number": i,
                "timestamp": "2025-11-23T10:00:00Z",
            })

        assert len(received_messages) == 3
        assert [m["sequence_number"] for m in received_messages] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_handle_new_message_out_of_order(self):
        """Test handling messages arriving out of order."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received_messages = []
        gap_detected = []

        client.set_on_message_ready(
            lambda msg: received_messages.append(msg)
        )
        client.set_on_ordering_gap_detected(
            lambda room_id: gap_detected.append(room_id)
        )

        # Message 1
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-1",
            "sequence_number": 1,
        })
        assert len(received_messages) == 1

        # Message 3 (skip 2)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-3",
            "sequence_number": 3,
        })
        assert len(received_messages) == 1  # Still 1
        assert len(gap_detected) == 1  # Gap detected

        # Message 2 arrives
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-2",
            "sequence_number": 2,
        })
        assert len(received_messages) == 3  # Now 2 and 3 are displayed

    @pytest.mark.asyncio
    async def test_handle_new_message_different_room(self):
        """Test that messages for other rooms are ignored."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received_messages = []
        client.set_on_message_ready(
            lambda msg: received_messages.append(msg)
        )

        # Message for different room
        await client._handle_new_message({
            "room_id": "room-456",
            "message_id": "msg-1",
            "sequence_number": 1,
        })

        assert len(received_messages) == 0

    @pytest.mark.asyncio
    async def test_handle_duplicate_message(self):
        """Test that duplicate messages trigger callback."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        duplicates = []
        client.set_on_duplicate_message(
            lambda msg_id: duplicates.append(msg_id)
        )

        message = {
            "room_id": "room-123",
            "message_id": "msg-1",
            "sequence_number": 1,
        }

        await client._handle_new_message(message)
        await client._handle_new_message(message)  # Duplicate

        assert len(duplicates) == 1
        assert duplicates[0] == "msg-1"

    @pytest.mark.asyncio
    async def test_handle_member_joined(self):
        """Test handling member joined notification."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        joined_members = []
        client.set_on_member_joined(
            lambda member: joined_members.append(member)
        )

        await client._handle_member_joined({
            "room_id": "room-123",
            "username": "bob",
            "member_count": 2,
            "timestamp": "2025-11-23T10:00:00Z",
        })

        assert len(joined_members) == 1
        assert joined_members[0]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_handle_member_joined_different_room(self):
        """Test that member_joined for other rooms is ignored."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        joined_members = []
        client.set_on_member_joined(
            lambda member: joined_members.append(member)
        )

        await client._handle_member_joined({
            "room_id": "room-456",
            "username": "bob",
        })

        assert len(joined_members) == 0


class TestChatClientProcessMessage:
    """Tests for ChatClient message processing."""

    @pytest.mark.asyncio
    async def test_process_new_message_type(self):
        """Test processing new_message type."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda msg: received.append(msg))

        message = json.dumps({
            "type": "new_message",
            "data": {
                "room_id": "room-123",
                "message_id": "msg-1",
                "sequence_number": 1,
                "username": "alice",
                "content": "Hello!",
            },
        })

        await client._process_incoming_message(message)

        assert len(received) == 1
        assert received[0]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_process_member_joined_type(self):
        """Test processing member_joined type."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        joined = []
        client.set_on_member_joined(lambda m: joined.append(m))

        message = json.dumps({
            "type": "member_joined",
            "data": {
                "room_id": "room-123",
                "username": "bob",
                "member_count": 2,
            },
        })

        await client._process_incoming_message(message)

        assert len(joined) == 1
        assert joined[0]["username"] == "bob"

    @pytest.mark.asyncio
    async def test_process_invalid_json(self):
        """Test processing invalid JSON."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        # Should not raise, just log error
        await client._process_incoming_message("not valid json")

    @pytest.mark.asyncio
    async def test_process_unknown_message_type(self):
        """Test processing unknown message type falls through."""
        client = ChatClient(node_url="ws://localhost:8000")

        received = []
        client.set_message_handler(lambda msg: received.append(msg))

        message = json.dumps({
            "type": "unknown_type",
            "data": {},
        })

        await client._process_incoming_message(message)

        # Should fall through to original handler
        assert len(received) == 1


class TestChatClientBufferAccess:
    """Tests for ChatClient buffer access methods."""

    def test_get_buffer_for_room(self):
        """Test getting buffer for specific room."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        buffer = client.get_buffer_for_room("room-123")
        assert buffer is not None
        assert isinstance(buffer, MessageBuffer)

        # Non-existent room
        buffer = client.get_buffer_for_room("room-999")
        assert buffer is None

    def test_get_buffered_message_count(self):
        """Test getting buffered message count."""
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        # Add some buffered (out of order) messages
        buffer = client.message_buffers["room-123"]
        buffer.add_message({"message_id": "msg-2", "sequence_number": 2})
        buffer.add_message({"message_id": "msg-3", "sequence_number": 3})

        assert client.get_buffered_message_count() == 2
        assert client.get_buffered_message_count("room-123") == 2

        # Non-existent room
        assert client.get_buffered_message_count("room-999") == 0


# Acceptance Test Scenarios


class TestAcceptanceScenarios:
    """Acceptance test scenarios from the issue."""

    @pytest.mark.asyncio
    async def test_scenario_1_in_order_messages(self):
        """
        Scenario 1: In-Order Messages
        Given: Client has joined a room
        When: Messages arrive with seq 1, 2, 3, 4
        Then: All messages are ready for display immediately in order
        """
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda msg: received.append(msg))

        for seq in [1, 2, 3, 4]:
            await client._handle_new_message({
                "room_id": "room-123",
                "message_id": f"msg-{seq}",
                "sequence_number": seq,
            })

        assert len(received) == 4
        assert [m["sequence_number"] for m in received] == [1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_scenario_2_out_of_order_messages(self):
        """
        Scenario 2: Out-of-Order Messages
        Given: Client has joined a room
        When: Messages arrive with seq 1, 3, 2, 4
        Then: Message 1 is ready immediately
              Message 3 is buffered
              Messages 2 and 3 are ready when 2 arrives
              Message 4 is ready immediately
        """
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda msg: received.append(msg))

        # Message 1
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-1",
            "sequence_number": 1,
        })
        assert len(received) == 1
        assert received[-1]["sequence_number"] == 1

        # Message 3 (buffered)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-3",
            "sequence_number": 3,
        })
        assert len(received) == 1  # Still 1

        # Message 2 (triggers 2 and 3)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-2",
            "sequence_number": 2,
        })
        assert len(received) == 3
        assert received[-2]["sequence_number"] == 2
        assert received[-1]["sequence_number"] == 3

        # Message 4 (ready immediately)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-4",
            "sequence_number": 4,
        })
        assert len(received) == 4
        assert received[-1]["sequence_number"] == 4

    @pytest.mark.asyncio
    async def test_scenario_3_gap_handling(self):
        """
        Scenario 3: Gap Handling
        Given: Client has seen messages 1-5
        When: Message 8 arrives (6 and 7 missing)
        Then: Message 8 is buffered
              Gap detection callback is triggered
              Messages 6, 7, 8 are ready when they arrive
        """
        client = ChatClient(node_url="ws://localhost:8000")
        client.set_current_room("room-123")

        received = []
        gaps = []
        client.set_on_message_ready(lambda msg: received.append(msg))
        client.set_on_ordering_gap_detected(
            lambda room_id: gaps.append(room_id)
        )

        # Messages 1-5
        for seq in range(1, 6):
            await client._handle_new_message({
                "room_id": "room-123",
                "message_id": f"msg-{seq}",
                "sequence_number": seq,
            })
        assert len(received) == 5

        # Message 8 (gap - 6, 7 missing)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-8",
            "sequence_number": 8,
        })
        assert len(received) == 5  # Still 5
        assert len(gaps) == 1  # Gap detected

        # Message 6
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-6",
            "sequence_number": 6,
        })
        assert len(received) == 6

        # Message 7 (triggers 7 and 8)
        await client._handle_new_message({
            "room_id": "room-123",
            "message_id": "msg-7",
            "sequence_number": 7,
        })
        assert len(received) == 8
        assert [m["sequence_number"] for m in received[-3:]] == [6, 7, 8]
