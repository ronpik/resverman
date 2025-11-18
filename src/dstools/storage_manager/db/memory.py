"""
In-memory database storage implementation.

This implementation stores all data in Python dictionaries with thread-safe
operations. Suitable for testing and development.
"""

import threading
import uuid
import copy
from typing import Dict, Any, List, Optional, Iterator, Tuple
from contextlib import contextmanager

from .base import BaseDBStorage, Record, RecordID, QueryFilter
from ..exceptions import (
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    OperationError,
)


class InMemoryDBStorage(BaseDBStorage):
    """
    In-memory database storage implementation.

    Features:
    - Thread-safe operations using locks
    - No persistence between runs
    - Fast operations with no I/O overhead
    - Support for basic queries (equality, filtering)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize in-memory storage.

        Args:
            config: Configuration dictionary with optional:
                - collections: List of collection names to pre-initialize
                - thread_safe: Enable thread-safe operations (default: True)
        """
        super().__init__(config)
        self._collections: Dict[str, Dict[RecordID, Record]] = {}
        self._connected = False
        self._thread_safe = config.get("thread_safe", True)

        if self._thread_safe:
            self._lock = threading.RLock()
        else:
            self._lock = _DummyLock()

        # Pre-initialize collections if specified
        for collection in config.get("collections", []):
            self._collections[self.get_full_collection_name(collection)] = {}

    def connect(self) -> None:
        """Establish connection (no-op for in-memory)."""
        self._connected = True

    def disconnect(self) -> None:
        """Close connection and clear data."""
        with self._lock:
            self._collections.clear()
            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def insert(
        self,
        collection: str,
        record: Record,
        record_id: Optional[RecordID] = None,
    ) -> RecordID:
        """Insert a new record."""
        self.validate_record(record)
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            # Ensure collection exists
            if full_collection not in self._collections:
                self._collections[full_collection] = {}

            # Generate or use provided ID
            if record_id is None:
                # Check if record has 'id' field
                if "id" in record:
                    record_id = record["id"]
                else:
                    record_id = str(uuid.uuid4())

            # Check for duplicates
            if record_id in self._collections[full_collection]:
                raise DuplicateRecordError(str(record_id), collection)

            # Store record with ID
            record_copy = copy.deepcopy(record)
            record_copy["id"] = record_id
            self._collections[full_collection][record_id] = record_copy

            return record_id

    def insert_many(self, collection: str, records: List[Record]) -> List[RecordID]:
        """Insert multiple records."""
        inserted_ids = []
        for record in records:
            record_id = self.insert(collection, record)
            inserted_ids.append(record_id)
        return inserted_ids

    def fetch(self, collection: str, record_id: RecordID) -> Record:
        """Fetch a single record by ID."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                raise RecordNotFoundError(str(record_id), collection)

            if record_id not in self._collections[full_collection]:
                raise RecordNotFoundError(str(record_id), collection)

            return copy.deepcopy(self._collections[full_collection][record_id])

    def fetch_many(self, collection: str, record_ids: List[RecordID]) -> List[Record]:
        """Fetch multiple records by IDs."""
        records = []
        for record_id in record_ids:
            try:
                record = self.fetch(collection, record_id)
                records.append(record)
            except RecordNotFoundError:
                # Skip records that don't exist
                pass
        return records

    def update(
        self,
        collection: str,
        record_id: RecordID,
        updates: Dict[str, Any],
        upsert: bool = False,
    ) -> None:
        """Update an existing record."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            # Ensure collection exists
            if full_collection not in self._collections:
                if upsert:
                    self._collections[full_collection] = {}
                else:
                    raise RecordNotFoundError(str(record_id), collection)

            # Check if record exists
            if record_id not in self._collections[full_collection]:
                if upsert:
                    # Insert new record
                    new_record = copy.deepcopy(updates)
                    new_record["id"] = record_id
                    self._collections[full_collection][record_id] = new_record
                else:
                    raise RecordNotFoundError(str(record_id), collection)
            else:
                # Update existing record
                record = self._collections[full_collection][record_id]
                for key, value in updates.items():
                    record[key] = value

    def update_many(
        self,
        collection: str,
        filters: QueryFilter,
        updates: Dict[str, Any],
    ) -> int:
        """Update multiple records matching filters."""
        matching_records = self.query(collection, filters)
        count = 0

        for record in matching_records:
            record_id = record.get("id")
            if record_id:
                self.update(collection, record_id, updates, upsert=False)
                count += 1

        return count

    def delete(self, collection: str, record_id: RecordID) -> bool:
        """Delete a record by ID."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                return False

            if record_id in self._collections[full_collection]:
                del self._collections[full_collection][record_id]
                return True

            return False

    def delete_many(self, collection: str, filters: QueryFilter) -> int:
        """Delete multiple records matching filters."""
        matching_records = self.query(collection, filters)
        count = 0

        for record in matching_records:
            record_id = record.get("id")
            if record_id and self.delete(collection, record_id):
                count += 1

        return count

    def exists(self, collection: str, record_id: RecordID) -> bool:
        """Check if a record exists."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                return False
            return record_id in self._collections[full_collection]

    def query(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Record]:
        """Query records with filters."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                return []

            # Get all records
            records = list(self._collections[full_collection].values())

            # Apply filters
            if filters:
                records = [r for r in records if self._matches_filters(r, filters)]

            # Apply ordering
            if order_by:
                for field, direction in reversed(order_by):
                    reverse = direction.lower() == "desc"
                    records.sort(
                        key=lambda x: x.get(field, ""),
                        reverse=reverse,
                    )

            # Apply offset and limit
            if offset:
                records = records[offset:]
            if limit:
                records = records[:limit]

            return [copy.deepcopy(r) for r in records]

    def query_one(
        self,
        collection: str,
        filters: QueryFilter,
    ) -> Optional[Record]:
        """Query for a single record."""
        results = self.query(collection, filters, limit=1)
        return results[0] if results else None

    def count(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
    ) -> int:
        """Count records matching filters."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                return 0

            if filters is None:
                return len(self._collections[full_collection])

            # Count matching records
            count = 0
            for record in self._collections[full_collection].values():
                if self._matches_filters(record, filters):
                    count += 1

            return count

    def iterate(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        batch_size: int = 100,
    ) -> Iterator[Record]:
        """Iterate over records in batches."""
        offset = 0
        while True:
            batch = self.query(
                collection,
                filters=filters,
                limit=batch_size,
                offset=offset,
            )
            if not batch:
                break

            for record in batch:
                yield record

            offset += batch_size

    def list_collections(self) -> List[str]:
        """List all collections."""
        with self._lock:
            # Remove prefix from collection names
            collections = []
            for name in self._collections.keys():
                if self._collection_prefix and name.startswith(self._collection_prefix):
                    collections.append(name[len(self._collection_prefix) :])
                else:
                    collections.append(name)
            return collections

    def collection_exists(self, collection: str) -> bool:
        """Check if collection exists."""
        full_collection = self.get_full_collection_name(collection)
        with self._lock:
            return full_collection in self._collections

    def create_collection(
        self,
        collection: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new collection."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection in self._collections:
                raise DuplicateRecordError(collection, "collection")

            self._collections[full_collection] = {}

    def drop_collection(self, collection: str) -> None:
        """Drop a collection."""
        full_collection = self.get_full_collection_name(collection)

        with self._lock:
            if full_collection not in self._collections:
                raise RecordNotFoundError(collection, "collection")

            del self._collections[full_collection]

    @contextmanager
    def transaction(self):
        """
        Context manager for transactions.

        Note: For in-memory storage, this provides a simple lock
        but doesn't support true rollback.
        """
        with self._lock:
            try:
                yield self
            except Exception:
                # In-memory storage doesn't support rollback
                raise

    def _matches_filters(self, record: Record, filters: QueryFilter) -> bool:
        """
        Check if record matches all filters.

        Args:
            record: Record to check
            filters: Filter dictionary

        Returns:
            True if record matches all filters
        """
        for key, value in filters.items():
            # Support nested field access with dot notation
            record_value = self._get_nested_value(record, key)

            if record_value != value:
                return False

        return True

    def _get_nested_value(self, record: Record, key: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            record: Record dictionary
            key: Key with dot notation (e.g., "metadata.user_id")

        Returns:
            Value at the nested path, or None if not found
        """
        keys = key.split(".")
        value = record

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return None
            else:
                return None

        return value


class _DummyLock:
    """Dummy lock for non-thread-safe mode."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
