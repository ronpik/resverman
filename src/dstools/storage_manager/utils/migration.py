"""
Migration utilities for storage manager.

This module provides utilities for migrating data between different
storage backends.
"""

from typing import Dict, Any, Optional, Callable
import logging

from ..db.base import BaseDBStorage
from ..object_store.base import BaseObjectStore
from ..exceptions import OperationError


logger = logging.getLogger(__name__)


def migrate_db_storage(
    source: BaseDBStorage,
    target: BaseDBStorage,
    collections: Optional[list] = None,
    batch_size: int = 100,
    transform: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Migrate data from one database storage to another.

    Args:
        source: Source database storage
        target: Target database storage
        collections: List of collections to migrate (None for all)
        batch_size: Batch size for migration
        transform: Optional transformation function for records

    Returns:
        Migration statistics
    """
    stats = {
        "collections_migrated": 0,
        "records_migrated": 0,
        "errors": 0,
    }

    # Get collections to migrate
    if collections is None:
        collections = source.list_collections()

    for collection in collections:
        logger.info(f"Migrating collection: {collection}")

        try:
            # Create collection in target
            if not target.collection_exists(collection):
                target.create_collection(collection)

            # Migrate records in batches
            for record in source.iterate(collection, batch_size=batch_size):
                try:
                    # Apply transformation if provided
                    if transform:
                        record = transform(record)

                    # Insert into target
                    target.insert(collection, record, record_id=record.get("id"))
                    stats["records_migrated"] += 1

                except Exception as e:
                    logger.error(f"Failed to migrate record: {e}")
                    stats["errors"] += 1

            stats["collections_migrated"] += 1

        except Exception as e:
            logger.error(f"Failed to migrate collection '{collection}': {e}")
            stats["errors"] += 1

    return stats


def migrate_object_store(
    source: BaseObjectStore,
    target: BaseObjectStore,
    prefix: Optional[str] = None,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Migrate objects from one object store to another.

    Args:
        source: Source object store
        target: Target object store
        prefix: Optional prefix filter
        batch_size: Batch size for migration

    Returns:
        Migration statistics
    """
    stats = {
        "objects_migrated": 0,
        "bytes_migrated": 0,
        "errors": 0,
    }

    # Get all object keys
    object_keys = source.list_objects(prefix=prefix)
    total = len(object_keys)

    logger.info(f"Migrating {total} objects...")

    for i, object_key in enumerate(object_keys):
        try:
            # Get object from source
            content = source.get(object_key)
            metadata = source.get_metadata(object_key)

            # Put object to target
            target.put(
                key=object_key,
                data=content,
                content_type=metadata.content_type,
                metadata=metadata.custom_metadata,
            )

            stats["objects_migrated"] += 1
            stats["bytes_migrated"] += len(content)

            if (i + 1) % batch_size == 0:
                logger.info(f"Migrated {i + 1}/{total} objects")

        except Exception as e:
            logger.error(f"Failed to migrate object '{object_key}': {e}")
            stats["errors"] += 1

    return stats
