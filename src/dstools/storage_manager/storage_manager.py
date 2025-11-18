"""
StorageManager orchestrator.

This module provides the main StorageManager class that coordinates
database storage and object store operations, providing a unified interface
for applications.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import logging

from .db.base import BaseDBStorage, Record, RecordID
from .object_store.base import BaseObjectStore, ObjectMetadata
from .exceptions import (
    ValidationError,
    ConsistencyError,
    OperationError,
    RecordNotFoundError,
    ObjectNotFoundError,
)


logger = logging.getLogger(__name__)


class StorageManager:
    """
    Storage manager that orchestrates database and object store operations.

    This class provides a unified interface for applications that need both
    structured data storage and binary object management, maintaining
    consistency between the two storage layers.
    """

    def __init__(
        self,
        db_storage: Optional[BaseDBStorage] = None,
        object_store: Optional[BaseObjectStore] = None,
        record_collection: str = "objects",
        object_key_field: str = "object_key",
        consistency_check_on_init: bool = False,
        cleanup_orphans_on_init: bool = False,
    ):
        """
        Initialize storage manager.

        Args:
            db_storage: Database storage instance
            object_store: Object store instance
            record_collection: Collection/table name for object records
            object_key_field: Field name for object store reference
            consistency_check_on_init: Validate DB-ObjectStore consistency on init
            cleanup_orphans_on_init: Remove orphaned objects on startup
        """
        if db_storage is None and object_store is None:
            raise ValidationError(
                "At least one of db_storage or object_store must be provided"
            )

        self.db_storage = db_storage
        self.object_store = object_store
        self.record_collection = record_collection
        self.object_key_field = object_key_field

        # Initialize connections
        if self.db_storage and not self.db_storage.is_connected():
            self.db_storage.connect()

        if self.object_store and not self.object_store.is_connected():
            self.object_store.connect()

        # Perform consistency check if requested
        if consistency_check_on_init:
            self._check_consistency()

        # Cleanup orphans if requested
        if cleanup_orphans_on_init:
            self.cleanup_orphans()

    def store_object(
        self,
        content: bytes,
        object_key: str,
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[RecordID] = None,
    ) -> RecordID:
        """
        Store object and create DB record.

        Operation flow:
        1. Upload to object store
        2. Create DB record with object reference
        3. On failure: cleanup uploaded object

        Args:
            content: Object content as bytes
            object_key: Key/path in object store
            metadata: Additional metadata for DB record
            record_id: Optional record ID

        Returns:
            Record ID

        Raises:
            ValidationError: If parameters are invalid
            OperationError: If operation fails
        """
        if self.object_store is None:
            raise ValidationError("Object store not configured")

        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        metadata = metadata or {}

        try:
            # 1. Upload to object store
            obj_metadata = self.object_store.put(
                key=object_key,
                data=content,
                content_type=metadata.get("content_type"),
                metadata=metadata.get("custom_metadata"),
            )

            # 2. Create DB record
            record = {
                self.object_key_field: object_key,
                "content_type": obj_metadata.content_type,
                "size_bytes": obj_metadata.size_bytes,
                "uploaded_at": datetime.now().isoformat(),
                "checksum": obj_metadata.checksum,
            }

            # Add additional metadata
            for key, value in metadata.items():
                if key not in record:
                    record[key] = value

            record_id = self.db_storage.insert(
                self.record_collection,
                record,
                record_id=record_id,
            )

            return record_id

        except Exception as e:
            # Cleanup: try to delete uploaded object
            try:
                if self.object_store.exists(object_key):
                    self.object_store.delete(object_key)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup object '{object_key}': {cleanup_error}")

            raise OperationError(f"Failed to store object: {e}")

    def fetch_object(
        self,
        record_id: RecordID,
    ) -> Tuple[bytes, Record]:
        """
        Fetch object content and metadata.

        Args:
            record_id: Record ID

        Returns:
            Tuple of (object content, record)

        Raises:
            RecordNotFoundError: If record not found
            ObjectNotFoundError: If object not found
            ConsistencyError: If object reference is invalid
        """
        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        if self.object_store is None:
            raise ValidationError("Object store not configured")

        # 1. Fetch record from DB
        record = self.db_storage.fetch(self.record_collection, record_id)

        # 2. Extract object key
        object_key = record.get(self.object_key_field)
        if not object_key:
            raise ConsistencyError(
                f"Record '{record_id}' missing object key field '{self.object_key_field}'",
                record_id=str(record_id),
            )

        # 3. Download from object store
        try:
            content = self.object_store.get(object_key)
        except ObjectNotFoundError:
            raise ConsistencyError(
                f"Object '{object_key}' not found for record '{record_id}'",
                record_id=str(record_id),
                object_key=object_key,
            )

        return content, record

    def get_object_content(self, record_id: RecordID) -> bytes:
        """
        Get object content only.

        Args:
            record_id: Record ID

        Returns:
            Object content
        """
        content, _ = self.fetch_object(record_id)
        return content

    def get_object_metadata(self, record_id: RecordID) -> Record:
        """
        Get object metadata only (DB record).

        Args:
            record_id: Record ID

        Returns:
            Record dictionary
        """
        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        return self.db_storage.fetch(self.record_collection, record_id)

    def update_object(
        self,
        record_id: RecordID,
        content: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update object content and/or metadata.

        Args:
            record_id: Record ID
            content: New object content (if updating object)
            metadata: New metadata fields

        Raises:
            RecordNotFoundError: If record not found
        """
        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        # Fetch existing record
        record = self.db_storage.fetch(self.record_collection, record_id)
        object_key = record.get(self.object_key_field)

        old_object_key = object_key

        try:
            # Update object if new content provided
            if content is not None:
                if self.object_store is None:
                    raise ValidationError("Object store not configured")

                # Generate new object key if needed (or reuse existing)
                if not object_key:
                    object_key = f"objects/{record_id}"

                # Upload new object
                obj_metadata = self.object_store.put(
                    key=object_key,
                    data=content,
                    content_type=metadata.get("content_type") if metadata else None,
                )

                # Update record with new object info
                updates = {
                    self.object_key_field: object_key,
                    "content_type": obj_metadata.content_type,
                    "size_bytes": obj_metadata.size_bytes,
                    "updated_at": datetime.now().isoformat(),
                    "checksum": obj_metadata.checksum,
                }
            else:
                updates = {}

            # Add metadata updates
            if metadata:
                updates.update(metadata)

            # Update DB record
            if updates:
                self.db_storage.update(
                    self.record_collection,
                    record_id,
                    updates,
                )

            # Delete old object if key changed
            if (
                content is not None
                and old_object_key
                and old_object_key != object_key
                and self.object_store
            ):
                try:
                    self.object_store.delete(old_object_key)
                except Exception as e:
                    logger.error(f"Failed to delete old object '{old_object_key}': {e}")

        except Exception as e:
            # Rollback: if we uploaded a new object, try to delete it
            if content is not None and object_key != old_object_key:
                try:
                    if self.object_store and self.object_store.exists(object_key):
                        self.object_store.delete(object_key)
                except Exception:
                    pass

            raise OperationError(f"Failed to update object: {e}")

    def delete_object(self, record_id: RecordID) -> None:
        """
        Delete object and DB record.

        Args:
            record_id: Record ID

        Raises:
            RecordNotFoundError: If record not found
        """
        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        # 1. Fetch record
        record = self.db_storage.fetch(self.record_collection, record_id)
        object_key = record.get(self.object_key_field)

        # 2. Delete from object store
        if object_key and self.object_store:
            try:
                self.object_store.delete(object_key)
            except Exception as e:
                logger.error(f"Failed to delete object '{object_key}': {e}")

        # 3. Delete DB record
        self.db_storage.delete(self.record_collection, record_id)

    def list_objects(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Record]:
        """
        List objects with metadata from DB.

        Args:
            filters: Query filters
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of records
        """
        if self.db_storage is None:
            raise ValidationError("Database storage not configured")

        return self.db_storage.query(
            self.record_collection,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    def store_objects_batch(
        self,
        objects: List[Tuple[str, bytes, Optional[Dict[str, Any]]]],
    ) -> List[Dict[str, Any]]:
        """
        Store multiple objects in batch.

        Args:
            objects: List of (object_key, content, metadata) tuples

        Returns:
            List of results with success status and record_id or error
        """
        results = []

        for object_key, content, metadata in objects:
            try:
                record_id = self.store_object(
                    content=content,
                    object_key=object_key,
                    metadata=metadata,
                )
                results.append({"success": True, "record_id": record_id})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return results

    def cleanup_orphans(self) -> Dict[str, int]:
        """
        Cleanup orphaned objects (objects without DB records).

        Returns:
            Dictionary with cleanup statistics
        """
        if self.object_store is None or self.db_storage is None:
            raise ValidationError("Both db_storage and object_store required")

        stats = {"checked": 0, "orphaned": 0, "deleted": 0, "errors": 0}

        # Get all object keys
        object_keys = self.object_store.list_objects()
        stats["checked"] = len(object_keys)

        # Check each object
        for object_key in object_keys:
            # Find record referencing this object
            records = self.db_storage.query(
                self.record_collection,
                filters={self.object_key_field: object_key},
                limit=1,
            )

            if not records:
                # Orphaned object
                stats["orphaned"] += 1
                try:
                    self.object_store.delete(object_key)
                    stats["deleted"] += 1
                except Exception as e:
                    logger.error(f"Failed to delete orphaned object '{object_key}': {e}")
                    stats["errors"] += 1

        return stats

    def _check_consistency(self) -> Dict[str, Any]:
        """
        Check consistency between DB and object store.

        Returns:
            Dictionary with consistency check results
        """
        if self.object_store is None or self.db_storage is None:
            return {"status": "skipped", "reason": "missing storage backend"}

        issues = {
            "missing_objects": [],  # Records without objects
            "orphaned_objects": [],  # Objects without records
        }

        # Check records for missing objects
        records = self.db_storage.query(self.record_collection)
        for record in records:
            object_key = record.get(self.object_key_field)
            if object_key and not self.object_store.exists(object_key):
                issues["missing_objects"].append(
                    {"record_id": record.get("id"), "object_key": object_key}
                )

        # Check objects for missing records
        object_keys = self.object_store.list_objects()
        for object_key in object_keys:
            records = self.db_storage.query(
                self.record_collection,
                filters={self.object_key_field: object_key},
                limit=1,
            )
            if not records:
                issues["orphaned_objects"].append(object_key)

        return {
            "status": "complete",
            "total_records": len(records),
            "total_objects": len(object_keys),
            "issues": issues,
        }

    def close(self) -> None:
        """Close connections to storage backends."""
        if self.db_storage:
            self.db_storage.disconnect()

        if self.object_store:
            self.object_store.disconnect()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
