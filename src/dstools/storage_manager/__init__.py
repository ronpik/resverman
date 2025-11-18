"""
Storage Abstraction Layer for DSTools.

This package provides a unified interface for database storage and object storage,
enabling seamless switching between different storage backends.

Example usage:
    # Create in-memory storage for testing
    >>> from dstools.storage_manager import create_storage_manager
    >>> manager = create_storage_manager(
    ...     db_type="memory",
    ...     object_store_type="filesystem_temp"
    ... )

    # Store an object
    >>> with open("photo.jpg", "rb") as f:
    ...     record_id = manager.store_object(
    ...         content=f.read(),
    ...         object_key="photos/photo.jpg",
    ...         metadata={"user_id": "user123"}
    ...     )

    # Retrieve object
    >>> content, metadata = manager.fetch_object(record_id)
"""

from typing import Dict, Any, Optional

# Core components
from .storage_manager import StorageManager
from .config import (
    StorageConfig,
    DBStorageConfig,
    ObjectStoreConfig,
    StorageManagerConfig,
    load_config,
)

# Database storage
from .db.base import BaseDBStorage, Record, RecordID, QueryFilter
from .db.memory import InMemoryDBStorage
from .db.sqlite import SQLiteDBStorage
from .db.postgresql import PostgreSQLDBStorage
from .db.mongodb import MongoDBStorage
from .db.firestore import FirestoreDBStorage

# Object storage
from .object_store.base import BaseObjectStore, ObjectMetadata
from .object_store.filesystem import (
    FilesystemObjectStore,
    TemporaryFilesystemObjectStore,
    PersistentFilesystemObjectStore,
)
from .object_store.s3 import (
    S3ObjectStore,
    S3Storage,
    MinIOStorage,
    DigitalOceanSpacesStorage,
)

# Exceptions
from .exceptions import (
    StorageException,
    ConfigurationError,
    InvalidConfigurationError,
    MissingCredentialsError,
    ConnectionError,
    DatabaseConnectionError,
    ObjectStoreConnectionError,
    OperationError,
    RecordNotFoundError,
    ObjectNotFoundError,
    DuplicateRecordError,
    ValidationError,
    ConsistencyError,
    ResourceError,
    InsufficientStorageError,
    QuotaExceededError,
    PermissionDeniedError,
    IntegrityError,
    ChecksumMismatchError,
    PartialOperationError,
)

# Utilities
from .utils import (
    validate_record,
    validate_object_key,
    check_consistency,
    repair_consistency,
)


__version__ = "0.1.0"

__all__ = [
    # Core
    "StorageManager",
    "create_storage_manager",
    "create_db_storage",
    "create_object_store",
    # Configuration
    "StorageConfig",
    "DBStorageConfig",
    "ObjectStoreConfig",
    "StorageManagerConfig",
    "load_config",
    # Database Storage
    "BaseDBStorage",
    "InMemoryDBStorage",
    "SQLiteDBStorage",
    "PostgreSQLDBStorage",
    "MongoDBStorage",
    "FirestoreDBStorage",
    "Record",
    "RecordID",
    "QueryFilter",
    # Object Storage
    "BaseObjectStore",
    "FilesystemObjectStore",
    "TemporaryFilesystemObjectStore",
    "PersistentFilesystemObjectStore",
    "S3ObjectStore",
    "S3Storage",
    "MinIOStorage",
    "DigitalOceanSpacesStorage",
    "ObjectMetadata",
    # Exceptions
    "StorageException",
    "ConfigurationError",
    "InvalidConfigurationError",
    "MissingCredentialsError",
    "ConnectionError",
    "DatabaseConnectionError",
    "ObjectStoreConnectionError",
    "OperationError",
    "RecordNotFoundError",
    "ObjectNotFoundError",
    "DuplicateRecordError",
    "ValidationError",
    "ConsistencyError",
    "ResourceError",
    "InsufficientStorageError",
    "QuotaExceededError",
    "PermissionDeniedError",
    "IntegrityError",
    "ChecksumMismatchError",
    "PartialOperationError",
    # Utilities
    "validate_record",
    "validate_object_key",
    "check_consistency",
    "repair_consistency",
]


# Factory functions


def create_db_storage(
    storage_type: str,
    config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> BaseDBStorage:
    """
    Create database storage instance.

    Args:
        storage_type: Type of storage ("memory", "sqlite", "postgresql", "mongodb", "firestore")
        config: Configuration dictionary
        **kwargs: Additional configuration parameters

    Returns:
        Database storage instance

    Example:
        >>> db = create_db_storage("memory")
        >>> db = create_db_storage("sqlite", database_path="/tmp/test.db")
    """
    config = config or {}
    config.update(kwargs)
    config["storage_type"] = storage_type

    storage_classes = {
        "memory": InMemoryDBStorage,
        "sqlite": SQLiteDBStorage,
        "postgresql": PostgreSQLDBStorage,
        "mongodb": MongoDBStorage,
        "firestore": FirestoreDBStorage,
    }

    storage_class = storage_classes.get(storage_type)
    if not storage_class:
        raise InvalidConfigurationError(
            f"Unknown storage type: {storage_type}. "
            f"Available types: {', '.join(storage_classes.keys())}"
        )

    return storage_class(config)


def create_object_store(
    storage_type: str,
    config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> BaseObjectStore:
    """
    Create object store instance.

    Args:
        storage_type: Type of storage ("filesystem", "filesystem_temp",
                     "filesystem_persistent", "s3", "minio", "do_spaces")
        config: Configuration dictionary
        **kwargs: Additional configuration parameters

    Returns:
        Object store instance

    Example:
        >>> store = create_object_store("filesystem_temp")
        >>> store = create_object_store("filesystem", base_path="/tmp/objects")
    """
    config = config or {}
    config.update(kwargs)
    config["storage_type"] = storage_type

    storage_classes = {
        "filesystem": FilesystemObjectStore,
        "filesystem_temp": TemporaryFilesystemObjectStore,
        "filesystem_persistent": PersistentFilesystemObjectStore,
        "s3": S3Storage,
        "minio": MinIOStorage,
        "do_spaces": DigitalOceanSpacesStorage,
    }

    storage_class = storage_classes.get(storage_type)
    if not storage_class:
        raise InvalidConfigurationError(
            f"Unknown storage type: {storage_type}. "
            f"Available types: {', '.join(storage_classes.keys())}"
        )

    return storage_class(config)


def create_storage_manager(
    db_type: Optional[str] = None,
    db_config: Optional[Dict[str, Any]] = None,
    object_store_type: Optional[str] = None,
    object_store_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> StorageManager:
    """
    Create storage manager with database and/or object store.

    Args:
        db_type: Database storage type
        db_config: Database configuration
        object_store_type: Object store type
        object_store_config: Object store configuration
        **kwargs: Additional StorageManager parameters

    Returns:
        StorageManager instance

    Example:
        >>> # For testing
        >>> manager = create_storage_manager(
        ...     db_type="memory",
        ...     object_store_type="filesystem_temp"
        ... )

        >>> # For local development
        >>> manager = create_storage_manager(
        ...     db_type="sqlite",
        ...     db_config={"database_path": "app.db"},
        ...     object_store_type="filesystem",
        ...     object_store_config={"base_path": "./storage"}
        ... )
    """
    db_storage = None
    object_store = None

    if db_type:
        db_storage = create_db_storage(db_type, db_config)

    if object_store_type:
        object_store = create_object_store(object_store_type, object_store_config)

    return StorageManager(
        db_storage=db_storage,
        object_store=object_store,
        **kwargs,
    )
