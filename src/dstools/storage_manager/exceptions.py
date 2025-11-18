"""
Exception hierarchy for the storage abstraction layer.

This module defines a comprehensive exception hierarchy for handling
errors in database storage and object store operations.
"""

from typing import Optional, Any, Dict


class StorageException(Exception):
    """Base exception for all storage-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Configuration Errors
class ConfigurationError(StorageException):
    """Base exception for configuration-related errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration parameters are invalid."""
    pass


class MissingCredentialsError(ConfigurationError):
    """Raised when required credentials are missing."""
    pass


# Connection Errors
class ConnectionError(StorageException):
    """Base exception for connection-related errors."""
    pass


class DatabaseConnectionError(ConnectionError):
    """Raised when database connection fails."""
    pass


class ObjectStoreConnectionError(ConnectionError):
    """Raised when object store connection fails."""
    pass


# Operation Errors
class OperationError(StorageException):
    """Base exception for operation-related errors."""
    pass


class RecordNotFoundError(OperationError):
    """Raised when a requested record is not found."""

    def __init__(self, record_id: str, collection: Optional[str] = None):
        message = f"Record '{record_id}' not found"
        if collection:
            message += f" in collection '{collection}'"
        super().__init__(message, {"record_id": record_id, "collection": collection})
        self.record_id = record_id
        self.collection = collection


class ObjectNotFoundError(OperationError):
    """Raised when a requested object is not found in object store."""

    def __init__(self, object_key: str):
        message = f"Object '{object_key}' not found"
        super().__init__(message, {"object_key": object_key})
        self.object_key = object_key


class DuplicateRecordError(OperationError):
    """Raised when attempting to insert a record with duplicate ID."""

    def __init__(self, record_id: str, collection: Optional[str] = None):
        message = f"Record with ID '{record_id}' already exists"
        if collection:
            message += f" in collection '{collection}'"
        super().__init__(message, {"record_id": record_id, "collection": collection})
        self.record_id = record_id
        self.collection = collection


class ValidationError(OperationError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message, {"field": field, "value": value})
        self.field = field
        self.value = value


class ConsistencyError(OperationError):
    """Raised when inconsistency is detected between DB and object store."""

    def __init__(
        self,
        message: str,
        record_id: Optional[str] = None,
        object_key: Optional[str] = None,
    ):
        super().__init__(
            message, {"record_id": record_id, "object_key": object_key}
        )
        self.record_id = record_id
        self.object_key = object_key


# Resource Errors
class ResourceError(StorageException):
    """Base exception for resource-related errors."""
    pass


class InsufficientStorageError(ResourceError):
    """Raised when storage space is insufficient."""
    pass


class QuotaExceededError(ResourceError):
    """Raised when storage quota is exceeded."""
    pass


class PermissionDeniedError(ResourceError):
    """Raised when operation is denied due to insufficient permissions."""

    def __init__(self, operation: str, resource: str):
        message = f"Permission denied for operation '{operation}' on '{resource}'"
        super().__init__(message, {"operation": operation, "resource": resource})
        self.operation = operation
        self.resource = resource


# Integrity Errors
class IntegrityError(StorageException):
    """Base exception for data integrity errors."""
    pass


class ChecksumMismatchError(IntegrityError):
    """Raised when checksum validation fails."""

    def __init__(self, expected: str, actual: str, object_key: Optional[str] = None):
        message = f"Checksum mismatch: expected {expected}, got {actual}"
        if object_key:
            message += f" for object '{object_key}'"
        super().__init__(
            message,
            {"expected": expected, "actual": actual, "object_key": object_key},
        )
        self.expected = expected
        self.actual = actual
        self.object_key = object_key


class PartialOperationError(IntegrityError):
    """Raised when a batch operation partially succeeds."""

    def __init__(
        self,
        message: str,
        successful: list,
        failed: list,
    ):
        super().__init__(
            message,
            {"successful_count": len(successful), "failed_count": len(failed)},
        )
        self.successful = successful
        self.failed = failed
