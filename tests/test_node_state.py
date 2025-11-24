import pytest
from src.node.state import NodeState


# ----------------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------------

@pytest.fixture
def sample_room():
    return {
        "room_id": "123",
        "room_name": "TestRoom",
        "description": "A test room",
        "node_id": "node-1",
        "members": ["user1"],
        "creator_id": "user1",
        "created_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def node_state():
    return NodeState()

# ----------------------------------------------------------------------------
# Test add_room()
# ----------------------------------------------------------------------------

def test_add_room_stores_room(node_state, sample_room):
    node_state.add_room(sample_room)

    # Verify it's stored by ID
    assert sample_room["room_id"] in node_state.rooms_by_id
    assert node_state.rooms_by_id[sample_room["room_id"]] == sample_room

    # Verify it's stored by name
    assert sample_room["room_name"] in node_state.rooms_by_name
    assert node_state.rooms_by_name[sample_room["room_name"]] == sample_room["room_id"]

def test_add_room_overwrites_with_same_name(node_state, sample_room):
    """Since class doesn't block duplicates, test overwrite behavior."""
    room1 = sample_room
    room2 = {
        **sample_room,
        "room_id": "456",  # different ID
        "description": "Updated room",
    }

    node_state.add_room(room1)
    node_state.add_room(room2)

    # room2 should overwrite room1's name mapping
    assert node_state.rooms_by_name["TestRoom"] == "456"
    assert node_state.get_room_by_name("TestRoom") == room2


# ----------------------------------------------------------------------------
# Test room_exists()
# ----------------------------------------------------------------------------

def test_room_exists(node_state, sample_room):
    assert not node_state.room_exists("TestRoom")

    node_state.add_room(sample_room)
    assert node_state.room_exists("TestRoom")


# ----------------------------------------------------------------------------
# Test get_room_by_id()
# ----------------------------------------------------------------------------

def test_get_room_by_id(node_state, sample_room):
    node_state.add_room(sample_room)

    fetched = node_state.get_room_by_id("123")
    assert fetched == sample_room


def test_get_room_by_id_missing(node_state):
    assert node_state.get_room_by_id("missing") is None


# ----------------------------------------------------------------------------
# Test get_room_by_name()
# ----------------------------------------------------------------------------

def test_get_room_by_name(node_state, sample_room):
    node_state.add_room(sample_room)

    fetched = node_state.get_room_by_name("TestRoom")
    assert fetched == sample_room


def test_get_room_by_name_missing(node_state):
    assert node_state.get_room_by_name("DoesNotExist") is None
