"""
Base Schema Classes

This module provides base classes for request and response schemas with
common serialization and deserialization methods to avoid code duplication.
"""

import json
from dataclasses import asdict, dataclass, fields
from typing import Any, Dict, TypeVar

T = TypeVar("T", bound="BaseResponse")


class BaseRequest:
    """
    Base class for request schemas.

    Provides common serialization methods for converting request objects
    to dictionary and JSON formats.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with 'type' key and optional 'data' key.
            If the request has no fields, only 'type' is included.
        """
        # Check if the dataclass has any fields
        if hasattr(self, "__dataclass_fields__") and fields(self):
            return {"type": self._message_type, "data": asdict(self)}
        return {"type": self._message_type}

    def to_json(self) -> str:
        """
        Convert to JSON string.

        Returns:
            JSON string representation of the request.
        """
        return json.dumps(self.to_dict())

    @property
    def _message_type(self) -> str:
        """
        Message type identifier for the request.

        Should be overridden by subclasses to provide the specific type.
        """
        raise NotImplementedError("Subclasses must define _message_type")


class BaseResponse:
    """
    Base class for response schemas.

    Provides common deserialization methods for creating response objects
    from dictionary and JSON formats.
    """

    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        """
        Create instance from dictionary.

        Args:
            data: Dictionary containing response data.

        Returns:
            Instance of the response class.
        """
        response_data = data.get("data", data)
        return cls._from_data(response_data)

    @classmethod
    def from_json(cls: type[T], json_str: str) -> T:
        """
        Create instance from JSON string.

        Args:
            json_str: JSON string containing response data.

        Returns:
            Instance of the response class.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def _from_data(cls: type[T], data: Dict[str, Any]) -> T:
        """
        Create instance from response data dictionary.

        Should be overridden by subclasses for custom deserialization.

        Args:
            data: Dictionary containing response data.

        Returns:
            Instance of the response class.
        """
        return cls(**data)


@dataclass
class BaseErrorResponse(BaseResponse):
    """
    Base class for error response schemas.

    Provides common structure for error responses with room_id, error message,
    and error code.

    Attributes:
        room_id: ID of the room related to the error
        error: Error message
        error_code: Error code (e.g., ROOM_NOT_FOUND, NOT_MEMBER)
    """

    room_id: str
    error: str
    error_code: str
