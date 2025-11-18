"""
Abstract base class for object storage implementations.

This module defines the interface that all object storage implementations
must follow, providing object management, metadata, and URL generation capabilities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator, Tuple, BinaryIO
from datetime import datetime
from dataclasses import dataclass

from ..exceptions import (
    ObjectNotFoundError,
    ValidationError,
    OperationError,
)


@dataclass
class ObjectMetadata:
    """Metadata for a stored object."""

    key: str
    size_bytes: int
    content_type: str
    last_modified: datetime
    checksum: Optional[str] = None
    custom_metadata: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "key": self.key,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "last_modified": self.last_modified.isoformat(),
            "checksum": self.checksum,
            "custom_metadata": self.custom_metadata or {},
        }


class BaseObjectStore(ABC):
    """
    Abstract base class for object storage implementations.

    All object storage backends must implement this interface to ensure
    consistent behavior across different storage types.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize object store.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self._base_path = config.get("base_path", "")

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to object store.

        Raises:
            ObjectStoreConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to object store.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connection is active.

        Returns:
            True if connected, False otherwise
        """
        pass

    # Object Management

    @abstractmethod
    def put(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ObjectMetadata:
        """
        Store an object.

        Args:
            key: Object key/path
            data: Object content as bytes
            content_type: MIME type (auto-detected if None)
            metadata: Custom metadata key-value pairs

        Returns:
            Object metadata

        Raises:
            ValidationError: If key or data is invalid
            OperationError: If upload fails
        """
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """
        Retrieve object content.

        Args:
            key: Object key/path

        Returns:
            Object content as bytes

        Raises:
            ObjectNotFoundError: If object not found
            OperationError: If download fails
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete an object.

        Args:
            key: Object key/path

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if an object exists.

        Args:
            key: Object key/path

        Returns:
            True if object exists, False otherwise
        """
        pass

    @abstractmethod
    def get_metadata(self, key: str) -> ObjectMetadata:
        """
        Get object metadata without downloading content.

        Args:
            key: Object key/path

        Returns:
            Object metadata

        Raises:
            ObjectNotFoundError: If object not found
        """
        pass

    # Batch Operations

    def put_many(
        self,
        objects: List[Tuple[str, bytes, Optional[str], Optional[Dict[str, str]]]],
    ) -> List[ObjectMetadata]:
        """
        Upload multiple objects.

        Args:
            objects: List of (key, data, content_type, metadata) tuples

        Returns:
            List of object metadata

        Raises:
            PartialOperationError: If some uploads fail
        """
        results = []
        for key, data, content_type, metadata in objects:
            obj_metadata = self.put(key, data, content_type, metadata)
            results.append(obj_metadata)
        return results

    def get_many(self, keys: List[str]) -> List[Tuple[str, bytes]]:
        """
        Download multiple objects.

        Args:
            keys: List of object keys

        Returns:
            List of (key, data) tuples (may be fewer than requested)
        """
        results = []
        for key in keys:
            try:
                data = self.get(key)
                results.append((key, data))
            except ObjectNotFoundError:
                # Skip objects that don't exist
                pass
        return results

    def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple objects.

        Args:
            keys: List of object keys

        Returns:
            Number of objects deleted
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    # Listing & Discovery

    @abstractmethod
    def list_objects(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[str]:
        """
        List object keys.

        Args:
            prefix: Filter by key prefix
            limit: Maximum number of keys to return
            offset: Number of keys to skip

        Returns:
            List of object keys
        """
        pass

    @abstractmethod
    def list_objects_with_metadata(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ObjectMetadata]:
        """
        List objects with their metadata.

        Args:
            prefix: Filter by key prefix
            limit: Maximum number of objects to return
            offset: Number of objects to skip

        Returns:
            List of object metadata
        """
        pass

    def iterate_objects(
        self,
        prefix: Optional[str] = None,
        batch_size: int = 100,
    ) -> Iterator[str]:
        """
        Iterate over object keys in batches.

        Args:
            prefix: Filter by key prefix
            batch_size: Number of objects per batch

        Yields:
            Object keys
        """
        offset = 0
        while True:
            batch = self.list_objects(prefix=prefix, limit=batch_size, offset=offset)
            if not batch:
                break

            for key in batch:
                yield key

            offset += batch_size

    # URL Generation (optional, implementation-specific)

    def get_url(
        self,
        key: str,
        expiration: Optional[int] = None,
    ) -> Optional[str]:
        """
        Generate a URL for accessing the object.

        Args:
            key: Object key/path
            expiration: URL expiration time in seconds (for signed URLs)

        Returns:
            URL string, or None if not supported

        Note: Not all backends support URL generation.
        """
        return None

    # Utility Methods

    def get_full_key(self, key: str) -> str:
        """
        Get full key with base path.

        Args:
            key: Base object key

        Returns:
            Full key with base path
        """
        if self._base_path:
            return f"{self._base_path.rstrip('/')}/{key.lstrip('/')}"
        return key

    def validate_key(self, key: str) -> None:
        """
        Validate object key.

        Args:
            key: Object key

        Raises:
            ValidationError: If key is invalid
        """
        if not key:
            raise ValidationError("Object key cannot be empty")

        # Check for invalid characters
        invalid_chars = ["\0", "\n", "\r"]
        for char in invalid_chars:
            if char in key:
                raise ValidationError(f"Object key contains invalid character: {repr(char)}")

    def detect_content_type(self, key: str, default: str = "application/octet-stream") -> str:
        """
        Detect content type from file extension.

        Args:
            key: Object key/path
            default: Default content type

        Returns:
            Content type string
        """
        import mimetypes

        content_type, _ = mimetypes.guess_type(key)
        return content_type or default

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
