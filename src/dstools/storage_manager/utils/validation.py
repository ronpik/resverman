"""
Validation utilities for storage manager.

This module provides validation functions for records and object keys.
"""

import json
from typing import Any, Dict

from ..exceptions import ValidationError


def validate_record(record: Dict[str, Any]) -> None:
    """
    Validate record data.

    Args:
        record: Record dictionary

    Raises:
        ValidationError: If record is invalid
    """
    if not isinstance(record, dict):
        raise ValidationError("Record must be a dictionary")

    if not record:
        raise ValidationError("Record cannot be empty")

    # Check for JSON-serializable values
    try:
        json.dumps(record)
    except (TypeError, ValueError) as e:
        raise ValidationError(f"Record contains non-JSON-serializable values: {e}")


def validate_object_key(key: str) -> None:
    """
    Validate object key.

    Args:
        key: Object key

    Raises:
        ValidationError: If key is invalid
    """
    if not key:
        raise ValidationError("Object key cannot be empty")

    if not isinstance(key, str):
        raise ValidationError("Object key must be a string")

    # Check for invalid characters
    invalid_chars = ["\0", "\n", "\r"]
    for char in invalid_chars:
        if char in key:
            raise ValidationError(f"Object key contains invalid character: {repr(char)}")

    # Check key length
    if len(key) > 1024:
        raise ValidationError("Object key too long (max 1024 characters)")


def validate_content_type(content_type: str) -> None:
    """
    Validate content type.

    Args:
        content_type: Content type string

    Raises:
        ValidationError: If content type is invalid
    """
    if not content_type:
        raise ValidationError("Content type cannot be empty")

    if not isinstance(content_type, str):
        raise ValidationError("Content type must be a string")

    # Basic MIME type validation
    if "/" not in content_type:
        raise ValidationError(f"Invalid content type format: {content_type}")
