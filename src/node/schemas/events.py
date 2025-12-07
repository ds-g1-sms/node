"""
Event Schema Definitions

Contains functions for creating standardized event data structures
for member join/leave, room deletion, etc.
"""

from typing import Dict, Any, Optional


def create_member_joined_event(
    room_id: str,
    username: str,
    member_count: int,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Create a member_joined event data structure.

    Args:
        room_id: Room ID where member joined
        username: Username of the joining member
        member_count: Total member count after join
        timestamp: ISO 8601 timestamp

    Returns:
        dict: Event data
    """
    return {
        "room_id": room_id,
        "username": username,
        "member_count": member_count,
        "timestamp": timestamp,
    }


def create_member_left_event(
    room_id: str,
    username: str,
    member_count: int,
    timestamp: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a member_left event data structure.

    Args:
        room_id: Room ID where member left
        username: Username of the leaving member
        member_count: Total member count after leave
        timestamp: ISO 8601 timestamp
        reason: Optional reason for leaving

    Returns:
        dict: Event data
    """
    event = {
        "room_id": room_id,
        "username": username,
        "member_count": member_count,
        "timestamp": timestamp,
    }
    if reason:
        event["reason"] = reason
    return event


def create_delete_room_initiated_event(
    room_id: str,
    initiator: str,
    transaction_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a delete_room_initiated event.

    Args:
        room_id: Room ID being deleted
        initiator: Username who initiated deletion
        transaction_id: Optional transaction ID

    Returns:
        dict: Event broadcast
    """
    data = {
        "room_id": room_id,
        "initiator": initiator,
        "status": "in_progress",
    }
    if transaction_id:
        data["transaction_id"] = transaction_id
    return {
        "type": "delete_room_initiated",
        "data": data,
    }


def create_room_deleted_event(
    room_id: str,
    room_name: str,
    transaction_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a room_deleted event.

    Args:
        room_id: Room ID that was deleted
        room_name: Name of the deleted room
        transaction_id: Optional transaction ID

    Returns:
        dict: Event broadcast
    """
    data = {
        "room_id": room_id,
        "room_name": room_name,
        "message": f"Room '{room_name}' has been deleted",
    }
    if transaction_id:
        data["transaction_id"] = transaction_id
    return {
        "type": "room_deleted",
        "data": data,
    }
