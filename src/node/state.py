
class NodeState:
    """
    Holds all local in-memory state for a server node.

    Responsibilities:
    - Track rooms by ID and by name
    - Provide storage for room metadata, members, and messages
    """

    def __init__(self):
        self.rooms_by_id = {}
        self.rooms_by_name = {}

    def add_room(self, room_obj):
        """
        Stores a new room in state
        """
        room_id = room_obj["room_id"]
        room_name = room_obj["room_name"]

        self.rooms_by_id[room_id] = room_obj
        self.rooms_by_name[room_name] = room_id

    def room_exists(self, room_name):
        """
        Returns True if a room with the given name exists locally.
        """
        return room_name in self.rooms_by_name

    def get_room_by_id(self, room_id):
        """
        Returns the full room object or None.
        """
        return self.rooms_by_id.get(room_id)

    def get_room_by_name(self, room_name):
        """
        Returns the full room object or None.
        """
        room_id = self.rooms_by_name.get(room_name)
        if room_id:
            return self.rooms_by_id[room_id]
        return None
