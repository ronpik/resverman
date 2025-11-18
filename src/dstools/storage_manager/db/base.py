"""
Abstract base class for database storage implementations.

This module defines the interface that all database storage implementations
must follow, providing CRUD operations and querying capabilities suitable
for both relational and NoSQL databases.
"""

from abc import ABC, abstractmethod
from typing import (
    Dict,
    Any,
    List,
    Optional,
    Iterator,
    Union,
    Tuple,
)
from contextlib import contextmanager

from ..exceptions import (
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    OperationError,
)


# Type aliases
Record = Dict[str, Any]
RecordID = Union[str, int]
QueryFilter = Dict[str, Any]


class BaseDBStorage(ABC):
    """
    Abstract base class for database storage implementations.

    All database storage backends must implement this interface to ensure
    consistent behavior across different storage types.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database storage.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self._collection_prefix = config.get("collection_prefix", "")

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to database.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to database.
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

    # Record Management

    @abstractmethod
    def insert(self, collection: str, record: Record, record_id: Optional[RecordID] = None) -> RecordID:
        """
        Insert a new record.

        Args:
            collection: Collection/table name
            record: Record data as dictionary
            record_id: Optional record ID (auto-generated if not provided)

        Returns:
            ID of inserted record

        Raises:
            DuplicateRecordError: If record with ID already exists
            ValidationError: If record data is invalid
        """
        pass

    @abstractmethod
    def insert_many(self, collection: str, records: List[Record]) -> List[RecordID]:
        """
        Insert multiple records.

        Args:
            collection: Collection/table name
            records: List of record dictionaries

        Returns:
            List of inserted record IDs

        Raises:
            ValidationError: If any record data is invalid
            PartialOperationError: If some insertions fail
        """
        pass

    @abstractmethod
    def fetch(self, collection: str, record_id: RecordID) -> Record:
        """
        Fetch a single record by ID.

        Args:
            collection: Collection/table name
            record_id: Record ID

        Returns:
            Record dictionary

        Raises:
            RecordNotFoundError: If record not found
        """
        pass

    @abstractmethod
    def fetch_many(self, collection: str, record_ids: List[RecordID]) -> List[Record]:
        """
        Fetch multiple records by IDs.

        Args:
            collection: Collection/table name
            record_ids: List of record IDs

        Returns:
            List of record dictionaries (may be fewer than requested if some not found)
        """
        pass

    @abstractmethod
    def update(
        self,
        collection: str,
        record_id: RecordID,
        updates: Dict[str, Any],
        upsert: bool = False,
    ) -> None:
        """
        Update an existing record.

        Args:
            collection: Collection/table name
            record_id: Record ID
            updates: Dictionary of fields to update
            upsert: If True, insert if record doesn't exist

        Raises:
            RecordNotFoundError: If record not found and upsert=False
            ValidationError: If update data is invalid
        """
        pass

    @abstractmethod
    def update_many(
        self,
        collection: str,
        filters: QueryFilter,
        updates: Dict[str, Any],
    ) -> int:
        """
        Update multiple records matching filters.

        Args:
            collection: Collection/table name
            filters: Query filters
            updates: Dictionary of fields to update

        Returns:
            Number of records updated
        """
        pass

    @abstractmethod
    def delete(self, collection: str, record_id: RecordID) -> bool:
        """
        Delete a record by ID.

        Args:
            collection: Collection/table name
            record_id: Record ID

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def delete_many(self, collection: str, filters: QueryFilter) -> int:
        """
        Delete multiple records matching filters.

        Args:
            collection: Collection/table name
            filters: Query filters

        Returns:
            Number of records deleted
        """
        pass

    @abstractmethod
    def exists(self, collection: str, record_id: RecordID) -> bool:
        """
        Check if a record exists.

        Args:
            collection: Collection/table name
            record_id: Record ID

        Returns:
            True if record exists, False otherwise
        """
        pass

    # Querying

    @abstractmethod
    def query(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Record]:
        """
        Query records with filters.

        Args:
            collection: Collection/table name
            filters: Query filters (field: value pairs for equality matching)
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: List of (field, direction) tuples for ordering
                     direction can be "asc" or "desc"

        Returns:
            List of matching records
        """
        pass

    @abstractmethod
    def query_one(
        self,
        collection: str,
        filters: QueryFilter,
    ) -> Optional[Record]:
        """
        Query for a single record.

        Args:
            collection: Collection/table name
            filters: Query filters

        Returns:
            Record if found, None otherwise
        """
        pass

    @abstractmethod
    def count(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
    ) -> int:
        """
        Count records matching filters.

        Args:
            collection: Collection/table name
            filters: Query filters (None for all records)

        Returns:
            Number of matching records
        """
        pass

    @abstractmethod
    def iterate(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        batch_size: int = 100,
    ) -> Iterator[Record]:
        """
        Iterate over records in batches.

        Args:
            collection: Collection/table name
            filters: Query filters
            batch_size: Number of records per batch

        Yields:
            Record dictionaries
        """
        pass

    # Collection/Table Management

    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        List all collections/tables.

        Returns:
            List of collection/table names
        """
        pass

    @abstractmethod
    def collection_exists(self, collection: str) -> bool:
        """
        Check if collection/table exists.

        Args:
            collection: Collection/table name

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    def create_collection(self, collection: str, schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Create a new collection/table.

        Args:
            collection: Collection/table name
            schema: Optional schema definition (implementation-specific)

        Raises:
            DuplicateRecordError: If collection already exists
        """
        pass

    @abstractmethod
    def drop_collection(self, collection: str) -> None:
        """
        Drop a collection/table.

        Args:
            collection: Collection/table name

        Raises:
            RecordNotFoundError: If collection doesn't exist
        """
        pass

    # Transaction Support

    @contextmanager
    @abstractmethod
    def transaction(self):
        """
        Context manager for transactions.

        Usage:
            with storage.transaction():
                storage.insert(...)
                storage.update(...)
                # Automatically commits on success, rolls back on exception

        Yields:
            Transaction context

        Raises:
            OperationError: If transaction fails
        """
        pass

    # Utility Methods

    def get_full_collection_name(self, collection: str) -> str:
        """
        Get full collection name with prefix.

        Args:
            collection: Base collection name

        Returns:
            Full collection name with prefix
        """
        if self._collection_prefix:
            return f"{self._collection_prefix}{collection}"
        return collection

    def validate_record(self, record: Record) -> None:
        """
        Validate record data.

        Args:
            record: Record dictionary

        Raises:
            ValidationError: If record is invalid
        """
        if not isinstance(record, dict):
            raise ValidationError("Record must be a dictionary")

        # Check for JSON-serializable values
        try:
            import json
            json.dumps(record)
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Record contains non-JSON-serializable values: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
