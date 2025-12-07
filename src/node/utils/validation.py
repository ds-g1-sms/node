"""
Validation Utilities

Contains utility functions for validating message content and other inputs.
"""

from typing import Tuple, Optional

# Message validation constants
MAX_MESSAGE_LENGTH = 5000


def validate_message_content(content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate message content.

    Args:
        content: The message content to validate

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: True if content is valid, False otherwise
            - error_message: Error message if invalid, None if valid
    """
    if not content:
        return False, "Message content cannot be empty"

    if len(content) > MAX_MESSAGE_LENGTH:
        return (
            False,
            f"Message content too long (max {MAX_MESSAGE_LENGTH} characters)",
        )

    return True, None
