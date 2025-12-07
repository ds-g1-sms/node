"""
Response Schema Definitions

Contains functions for creating standardized response structures.
"""

from typing import Dict, Any, Optional


def create_error_response(
    error_message: str,
    error_type: str = "error",
) -> Dict[str, Any]:
    """
    Create a generic error response.

    Args:
        error_message: Error message text
        error_type: Type of error response

    Returns:
        dict: Error response
    """
    return {
        "type": error_type,
        "data": {
            "success": False,
            "message": error_message,
        },
    }


def create_success_response(
    message: str,
    response_type: str = "success",
    additional_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a generic success response.

    Args:
        message: Success message text
        response_type: Type of success response
        additional_data: Optional additional data to include

    Returns:
        dict: Success response
    """
    response = {
        "type": response_type,
        "data": {
            "success": True,
            "message": message,
        },
    }
    if additional_data:
        response["data"].update(additional_data)
    return response


def create_join_error_response(
    room_id: str,
    error: str,
    error_code: str,
) -> Dict[str, Any]:
    """
    Create a join_room error response.

    Args:
        room_id: Room ID
        error: Error message
        error_code: Error code

    Returns:
        dict: Error response
    """
    return {
        "type": "join_room_error",
        "data": {
            "room_id": room_id,
            "error": error,
            "error_code": error_code,
        },
    }
