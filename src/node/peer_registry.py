"""
Peer Node Registry

Manages the registry of peer nodes in the distributed system.
"""

import logging
from typing import Dict, List
from xmlrpc.client import ServerProxy, Fault
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class PeerRegistry:
    """
    Manages peer node connections and communication.

    This class maintains a registry of peer nodes and provides
    methods to query them via XML-RPC.
    """

    def __init__(self, node_id: str, timeout: int = 3):
        """
        Initialize the peer registry.

        Args:
            node_id: Unique identifier for this node
            timeout: Default timeout for XML-RPC calls in seconds
        """
        self.node_id = node_id
        self.timeout = timeout
        self._peers: Dict[str, str] = {}  # node_id -> node_address

    def register_peer(self, node_id: str, node_address: str):
        """
        Register a peer node.

        Args:
            node_id: Unique identifier for the peer node
            node_address: XML-RPC address of the peer node (e.g., "http://node2:9090")
        """
        self._peers[node_id] = node_address
        logger.info(f"Registered peer node: {node_id} at {node_address}")

    def get_peer_address(self, node_id: str) -> str:
        """
        Get the address of a peer node.

        Args:
            node_id: The node ID to look up

        Returns:
            The node address if found, None otherwise
        """
        return self._peers.get(node_id)

    def list_peers(self) -> Dict[str, str]:
        """
        Get all registered peer nodes.

        Returns:
            Dictionary mapping node_id -> node_address
        """
        return self._peers.copy()

    def query_peer_rooms(self, node_id: str, node_address: str) -> List[Dict]:
        """
        Query a single peer node for its hosted rooms.

        Args:
            node_id: ID of the peer node
            node_address: XML-RPC address of the peer node

        Returns:
            List of room dictionaries from the peer node

        Raises:
            Exception: If the XML-RPC call fails
        """
        try:
            logger.debug(f"Querying peer node {node_id} at {node_address}")

            # Create XML-RPC proxy
            proxy = ServerProxy(node_address, allow_none=True)

            # Set timeout (note: this is a workaround for Python's xmlrpc.client)
            import socket

            old_timeout = socket.getdefaulttimeout()
            try:
                socket.setdefaulttimeout(self.timeout)
                rooms = proxy.get_hosted_rooms()
                logger.info(
                    f"Successfully queried {node_id}: {len(rooms)} rooms"
                )
                return rooms
            finally:
                socket.setdefaulttimeout(old_timeout)

        except Fault as e:
            logger.error(f"XML-RPC fault from {node_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to query {node_id}: {e}")
            raise

    def discover_global_rooms(self, local_rooms: List[Dict]) -> Dict[str, any]:
        """
        Query all peer nodes for their hosted rooms and aggregate results.

        Args:
            local_rooms: List of rooms hosted by the local node

        Returns:
            dict: Aggregated room information with structure:
            {
                'rooms': List[Dict],
                'total_count': int,
                'nodes_queried': List[str],
                'nodes_available': List[str],
                'nodes_unavailable': List[str]
            }
        """
        all_rooms = list(local_rooms)  # Start with local rooms
        nodes_queried = [self.node_id]
        available_nodes = [self.node_id]
        unavailable_nodes = []

        peers = self.list_peers()
        if not peers:
            logger.info("No peer nodes registered")
            return {
                "rooms": all_rooms,
                "total_count": len(all_rooms),
                "nodes_queried": nodes_queried,
                "nodes_available": available_nodes,
                "nodes_unavailable": unavailable_nodes,
            }

        # Query all peers in parallel
        with ThreadPoolExecutor(max_workers=len(peers)) as executor:
            future_to_node = {
                executor.submit(
                    self.query_peer_rooms, node_id, node_addr
                ): node_id
                for node_id, node_addr in peers.items()
            }

            for future in as_completed(future_to_node):
                node_id = future_to_node[future]
                nodes_queried.append(node_id)
                try:
                    rooms = future.result()
                    all_rooms.extend(rooms)
                    available_nodes.append(node_id)
                except Exception as e:
                    unavailable_nodes.append(node_id)
                    logger.warning(f"Failed to query node {node_id}: {e}")

        logger.info(
            f"Global room discovery complete: {len(all_rooms)} rooms from "
            f"{len(available_nodes)} available nodes "
            f"({len(unavailable_nodes)} unavailable)"
        )

        return {
            "rooms": all_rooms,
            "total_count": len(all_rooms),
            "nodes_queried": nodes_queried,
            "nodes_available": available_nodes,
            "nodes_unavailable": unavailable_nodes,
        }
