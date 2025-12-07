"""
Message Schema Definitions

Contains functions for creating standardized message data structures.
"""

from typing import Dict, Any


def create_message_data(
    message_id: str,
    room_id: str,
    username: str,
    content: str,
    sequence_number: int,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Create a standardized message data structure.

    Args:
        message_id: Unique identifier for the message
        room_id: Room ID where message was sent
        username: Username of the sender
        content: Message content
        sequence_number: Sequential number assigned by room admin
        timestamp: ISO 8601 timestamp

    Returns:
        dict: Standardized message data
    """
    return {
        "message_id": message_id,
        "room_id": room_id,
        "username": username,
        "content": content,
        "sequence_number": sequence_number,
        "timestamp": timestamp,
    }


def create_message_sent_confirmation(
    room_id: str,
    message_id: str,
    sequence_number: int,
    timestamp: str,
) -> Dict[str, Any]:
    """
    Create a message_sent confirmation response.

    Args:
        room_id: Room ID where message was sent
        message_id: ID of the sent message
        sequence_number: Assigned sequence number
        timestamp: Message timestamp

    Returns:
        dict: Confirmation response
    """
    return {
        "type": "message_sent",
        "data": {
            "room_id": room_id,
            "message_id": message_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
        },
    }


def create_message_error(
    room_id: str,
    error: str,
    error_code: str,
) -> Dict[str, Any]:
    """
    Create a message_error response.

    Args:
        room_id: Room ID where error occurred
        error: Error message
        error_code: Error code

    Returns:
        dict: Error response
    """
    return {
        "type": "message_error",
        "data": {
            "room_id": room_id,
            "error": error,
            "error_code": error_code,
        },
    }


def create_new_message_broadcast(
    message_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a new_message broadcast.

    Args:
        message_data: Message data from create_message_data

    Returns:
        dict: Broadcast message
    """
    return {
        "type": "new_message",
        "data": message_data,
    }
