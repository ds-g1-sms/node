"""
Broadcast Utilities

Contains utility functions for broadcasting messages and events to peer nodes.
"""

import logging
from typing import Dict, Any, Optional
from xmlrpc.client import ServerProxy

logger = logging.getLogger(__name__)


def broadcast_to_peers(
    peer_registry,
    room_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    exclude_node: Optional[str] = None,
):
    """
    Broadcast an event to all peer nodes via XML-RPC.

    This is a utility function to reduce code duplication when broadcasting
    member events or messages to peer nodes.

    Args:
        peer_registry: PeerRegistry instance for getting peer addresses
        room_id: The room ID for the event
        event_type: Type of event (e.g., "member_joined", "member_left")
        event_data: Event data to broadcast
        exclude_node: Optional node ID to exclude from broadcast
    """
    if not peer_registry:
        return

    peers = peer_registry.list_peers()
    for peer_node_id, peer_addr in peers.items():
        if peer_node_id == exclude_node:
            continue

        try:
            proxy = ServerProxy(peer_addr, allow_none=True)
            proxy.receive_member_event_broadcast(
                room_id, event_type, event_data
            )
            logger.debug(f"Broadcasted {event_type} to peer {peer_node_id}")
        except Exception as e:
            logger.error(
                f"Failed to broadcast {event_type} to {peer_node_id}: {e}"
            )


def broadcast_message_to_peers(
    peer_registry,
    room_id: str,
    message_data: Dict[str, Any],
):
    """
    Broadcast a message to all peer nodes via XML-RPC.

    Args:
        peer_registry: PeerRegistry instance for getting peer addresses
        room_id: The room ID for the message
        message_data: Message data to broadcast
    """
    if not peer_registry:
        return

    peers = peer_registry.list_peers()
    for peer_node_id, peer_addr in peers.items():
        try:
            proxy = ServerProxy(peer_addr, allow_none=True)
            proxy.receive_message_broadcast(room_id, message_data)
            logger.debug(f"Broadcasted message to peer {peer_node_id}")
        except Exception as e:
            logger.error(f"Failed to broadcast message to {peer_node_id}: {e}")
