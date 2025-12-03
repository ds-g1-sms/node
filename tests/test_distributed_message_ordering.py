
import pytest
from src.client import MessageBuffer, ChatClient




class TestDistributedMessageOrderingIntegration:
    """
    Integration tests for message ordering across multiple server nodes.
    """

    @pytest.mark.asyncio
    async def test_messages_from_multiple_nodes_arrive_in_master_order(self):
        """
        Tests if messages appear in masters order at the other nodes
        """

        # Client connected to node
        client = ChatClient(node_url="ws://node-a:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda msg: received.append(msg))

        # simulated messages from different nodes the master received
        messages_from_master = [
            {"room_id": "room-123", "message_id": "a1", "sequence_number": 1, "content": "from A"},
            {"room_id": "room-123", "message_id": "b1", "sequence_number": 2, "content": "from B"},
            {"room_id": "room-123", "message_id": "a2", "sequence_number": 3, "content": "from A again"},
        ]

        # Deliver to client in random order to simulate network variance
        await client._handle_new_message(messages_from_master[1])
        await client._handle_new_message(messages_from_master[0])
        await client._handle_new_message(messages_from_master[2])

        assert [m["sequence_number"] for m in received] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_gap_recovery_across_nodes(self):
        """
        Tests how gaps are handled and that messages still stay in order
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

        assert len(received) == 1
        assert len(gaps) == 1

        # late message 2
        await client._handle_new_message({
            "room_id": "room-123", "message_id": "m2", "sequence_number": 2,
        })

        assert [m["sequence_number"] for m in received] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_messages_from_multiple_nodes_dont_duplicate(self):
        """
        Tests if duplicated messages get ignored
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
        await client._handle_new_message(msg)

        assert len(received) == 1
        assert duplicates == ["shared-msg"]

    @pytest.mark.asyncio
    async def test_cross_node_burst_of_out_of_order_messages(self):
        """
        Tests if master handles message burst and still provides order
        """

        client = ChatClient(node_url="ws://node-d:8000")
        client.set_current_room("room-123")

        received = []
        client.set_on_message_ready(lambda m: received.append(m))

        # Messages assigned by the master node
        authoritative = [
            {"room_id": "room-123", "message_id": f"msg-{i}", "sequence_number": i}
            for i in range(1, 7)
        ]

        # random delivery order
        import random
        shuffled = authoritative.copy()
        random.shuffle(shuffled)

        for msg in shuffled:
            await client._handle_new_message(msg)

        assert [m["sequence_number"] for m in received] == [1, 2, 3, 4, 5, 6]

    @pytest.mark.asyncio
    async def test_multi_room_multi_node_isolation(self):
        """
        Tests if message ordering works with 2 chat rooms and 
        mixed messages from different nodes and rooms
        """

        client = ChatClient(node_url="ws://node-e:8000")
        client.set_current_room("room-1")

        received_room1 = []
        received_room2 = []

        # Room 1
        client.set_on_message_ready(lambda m: received_room1.append(m))

        # Room 2 with own buffer
        buf2 = MessageBuffer()
        client.message_buffers["room-2"] = buf2

        # Simulate messages across rooms from different nodes
        mixed = [
            {"room_id": "room-1", "message_id": "a1", "sequence_number": 1},
            {"room_id": "room-2", "message_id": "b2", "sequence_number": 2},
            {"room_id": "room-1", "message_id": "a2", "sequence_number": 2},
            {"room_id": "room-2", "message_id": "b1", "sequence_number": 1},
            {"room_id": "room-1", "message_id": "a3", "sequence_number": 3},
        ]

        for msg in mixed:
            if msg["room_id"] == "room-1":
                await client._handle_new_message(msg)
            else:
                # simulate buffer processing for another room
                buf2.add_message(msg)

        # Room 1
        assert [m["sequence_number"] for m in received_room1] == [1, 2, 3]

        # Room 2
        assert [m["sequence_number"] for m in buf2.get_new_messages()] == [1, 2]
