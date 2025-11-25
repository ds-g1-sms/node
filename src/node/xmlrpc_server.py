"""
XML-RPC Server for Inter-Node Communication

Handles XML-RPC requests from peer nodes for distributed operations.
"""

import logging
from xmlrpc.server import SimpleXMLRPCServer
from threading import Thread
from typing import List, Dict

from .room_state import RoomStateManager

logger = logging.getLogger(__name__)


class XMLRPCServer:
    """
    XML-RPC server for handling inter-node communication.

    Exposes methods that can be called by peer nodes to coordinate
    distributed operations like room discovery.
    """

    def __init__(
        self,
        room_manager: RoomStateManager,
        host: str,
        port: int,
        node_address: str,
    ):
        """
        Initialize the XML-RPC server.

        Args:
            room_manager: The room state manager instance
            host: Host address to bind to
            port: Port to listen on
            node_address: Full address of this node (e.g., "http://localhost:9090")
        """
        self.room_manager = room_manager
        self.host = host
        self.port = port
        self.node_address = node_address
        self.server = None
        self.server_thread = None

    def start(self):
        """Start the XML-RPC server in a background thread."""
        self.server = SimpleXMLRPCServer(
            (self.host, self.port),
            allow_none=True,
            logRequests=False,
        )

        # Register methods
        self.server.register_function(self.get_hosted_rooms, "get_hosted_rooms")

        logger.info(f"XML-RPC server starting on {self.host}:{self.port}")

        # Start server in background thread
        self.server_thread = Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"XML-RPC server started at {self.node_address}")

    def _run_server(self):
        """Run the XML-RPC server (called in background thread)."""
        self.server.serve_forever()

    def stop(self):
        """Stop the XML-RPC server."""
        if self.server:
            logger.info("Stopping XML-RPC server")
            self.server.shutdown()
            if self.server_thread:
                self.server_thread.join(timeout=2)
            logger.info("XML-RPC server stopped")

    def get_hosted_rooms(self) -> List[Dict]:
        """
        Returns a list of rooms hosted by this node.

        This method is exposed via XML-RPC and can be called by peer nodes.

        Returns:
            list: List of room dictionaries with structure:
            [
                {
                    'room_id': str,
                    'room_name': str,
                    'description': str,
                    'member_count': int,
                    'admin_node': str,
                    'node_address': str
                },
                ...
            ]
        """
        logger.info("XML-RPC: get_hosted_rooms called")

        # Get rooms from room manager
        rooms = self.room_manager.list_rooms()

        # Add node_address to each room
        for room in rooms:
            room["node_address"] = self.node_address

        logger.info(f"XML-RPC: Returning {len(rooms)} hosted rooms")
        return rooms
