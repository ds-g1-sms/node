
import pytest
from src.client import MessageBuffer, ChatClient




class TestDistributedMessageOrderingIntegration:
    """
    Integration tests for message ordering across multiple server nodes.
    Each node may receive client messages, but the room's master node
    is responsible for generating the authoritative sequence numbers.
    """

    @pytest.mark.asyncio
    async def test_messages_from_multiple_nodes_arrive_in_master_order(self):
        """
        Scenario: Clients send messages through different nodes.
        The master node assigns authoritative sequence numbers.
        The client must display them in correct master order.
        """

        # Client connected to node A
        client = ChatClient(node_url="ws://node-a:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda msg: received.append(msg))

        # Simulate messages routed through different nodes
        # Node B forwards user's message to the master node
        # The master node outputs ordered messages with seq numbers
        messages_from_master = [
            {"room_id": "room-123", "message_id": "a1", "sequence_number": 1, "content": "from A"},
            {"room_id": "room-123", "message_id": "b1", "sequence_number": 2, "content": "from B"},
            {"room_id": "room-123", "message_id": "a2", "sequence_number": 3, "content": "from A again"},
        ]

        # Deliver to client in random order to simulate network variance
        await client._handle_new_message(messages_from_master[1])  # seq 2
        await client._handle_new_message(messages_from_master[0])  # seq 1
        await client._handle_new_message(messages_from_master[2])  # seq 3

        assert [m["sequence_number"] for m in received] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_gap_recovery_across_nodes(self):
        """
        Scenario:
        - Client receives seq 1 and seq 3 (seq 2 missing)
        - seq 2 arrives later from a different node
        """

        client = ChatClient(node_url="ws://node-a:8000")
        client.set_current_room("room-123")

        received = []
        gaps = []
        client.set_on_message_ready(lambda m: received.append(m))
        client.set_on_ordering_gap_detected(lambda r: gaps.append(r))

        # Out-of-order due to routing differences
        await client._handle_new_message({
            "room_id": "room-123", "message_id": "m1", "sequence_number": 1,
        })
        await client._handle_new_message({
            "room_id": "room-123", "message_id": "m3", "sequence_number": 3,
        })

        assert len(received) == 1      # only seq 1
        assert len(gaps) == 1          # gap detected

        # Later comes message 2 from a different node
        await client._handle_new_message({
            "room_id": "room-123", "message_id": "m2", "sequence_number": 2,
        })

        assert [m["sequence_number"] for m in received] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_messages_from_multiple_nodes_dont_duplicate(self):
        """
        Scenario:
        - Two nodes forward the same message due to network retries
        - Client must detect and ignore the duplicate
        """

        client = ChatClient(node_url="ws://node-c:8000")
        client.set_current_room("room-123")

        received = []
        duplicates = []
        client.set_on_message_ready(lambda m: received.append(m))
        client.set_on_duplicate_message(lambda m_id: duplicates.append(m_id))

        # Two nodes send the same authoritative message from master
        msg = {
            "room_id": "room-123",
            "message_id": "shared-msg",
            "sequence_number": 1,
        }

        await client._handle_new_message(msg)
        await client._handle_new_message(msg)  # duplicate from another node

        assert len(received) == 1
        assert duplicates == ["shared-msg"]

    @pytest.mark.asyncio
    async def test_cross_node_burst_of_out_of_order_messages(self):
        """
        Scenario:
        - A burst of messages from multiple nodes arrives in totally random order.
        - Master-generated sequence numbers ensure ordering after buffering.
        """

        client = ChatClient(node_url="ws://node-d:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda m: received.append(m))

        # Messages 1–6 assigned by the master node
        authoritative = [
            {"room_id": "room-123", "message_id": f"msg-{i}", "sequence_number": i}
            for i in range(1, 7)
        ]

        # Shuffle delivery order as if coming from different nodes with delay
        import random
        shuffled = authoritative.copy()
        random.shuffle(shuffled)

        for msg in shuffled:
            await client._handle_new_message(msg)

        assert [m["sequence_number"] for m in received] == [1, 2, 3, 4, 5, 6]

    @pytest.mark.asyncio
    async def test_multi_room_multi_node_isolation(self):
        """
        Scenario:
        - Client receives messages for two rooms from multiple nodes.
        - Ordering must be maintained separately per room.
        """

        client = ChatClient(node_url="ws://node-e:8000")
        client.set_current_room("room-1")

        received_room1 = []
        received_room2 = []

        # Room 1 is the joined room
        client.set_on_message_ready(lambda m: received_room1.append(m))

        # Room 2 has its own buffer
        buf2 = MessageBuffer()
        client.message_buffers["room-2"] = buf2

        # Simulate messages across rooms from different nodes
        mixed = [
            {"room_id": "room-1", "message_id": "a1", "sequence_number": 1},
            {"room_id": "room-2", "message_id": "b2", "sequence_number": 2},
            {"room_id": "room-2", "message_id": "b1", "sequence_number": 1},
            {"room_id": "room-1", "message_id": "a2", "sequence_number": 2},
        ]

        # Process all
        for msg in mixed:
            if msg["room_id"] == "room-1":
                await client._handle_new_message(msg)
            else:
                # Manually simulate buffer processing for another room
                buf2.add_message(msg)

        # Room 1 ordering
        assert [m["sequence_number"] for m in received_room1] == [1, 2]

        # Room 2 ordering
        assert [m["sequence_number"] for m in buf2.get_new_messages()] == [1, 2]
