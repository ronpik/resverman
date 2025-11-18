"""
SQLite database storage implementation.

This implementation uses SQLite as the backend, providing file-based
persistent storage suitable for local development and small deployments.
"""

import sqlite3
import json
import uuid
import threading
from typing import Dict, Any, List, Optional, Iterator, Tuple
from contextlib import contextmanager
from pathlib import Path

from .base import BaseDBStorage, Record, RecordID, QueryFilter
from ..exceptions import (
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    DatabaseConnectionError,
    OperationError,
)


class SQLiteDBStorage(BaseDBStorage):
    """
    SQLite database storage implementation.

    Features:
    - File-based persistent storage
    - ACID transactions
    - Automatic schema creation
    - JSON column for flexible data
    - Thread-safe with connection pooling
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SQLite storage.

        Args:
            config: Configuration dictionary with:
                - database_path: Path to SQLite database file (":memory:" for in-memory)
                - timeout: Lock timeout in seconds (default: 5.0)
                - auto_create_tables: Auto-create tables (default: True)
                - journal_mode: Journal mode (default: "WAL")
        """
        super().__init__(config)
        self._database_path = config.get("database_path")
        if not self._database_path:
            raise ValidationError("database_path is required for SQLite storage")

        self._timeout = config.get("timeout", 5.0)
        self._auto_create_tables = config.get("auto_create_tables", True)
        self._journal_mode = config.get("journal_mode", "WAL")

        # Thread-local storage for connections
        self._local = threading.local()
        self._connected = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            try:
                conn = sqlite3.connect(
                    self._database_path,
                    timeout=self._timeout,
                    check_same_thread=False,
                )
                conn.row_factory = sqlite3.Row

                # Set journal mode
                if self._database_path != ":memory:":
                    conn.execute(f"PRAGMA journal_mode={self._journal_mode}")

                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys=ON")

                self._local.connection = conn
            except sqlite3.Error as e:
                raise DatabaseConnectionError(f"Failed to connect to SQLite: {e}")

        return self._local.connection

    def connect(self) -> None:
        """Establish connection to database."""
        # Create database file directory if needed
        if self._database_path != ":memory:":
            db_path = Path(self._database_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self._get_connection()
        self._connected = True

    def disconnect(self) -> None:
        """Close connection to database."""
        if hasattr(self._local, "connection") and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected

    def _ensure_table_exists(self, collection: str) -> None:
        """
        Ensure table exists for collection.

        Args:
            collection: Collection name
        """
        if not self._auto_create_tables:
            return

        full_collection = self.get_full_collection_name(collection)
        conn = self._get_connection()

        # Create table if it doesn't exist
        # We use a JSON column for flexible schema
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {full_collection} (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        conn.commit()

    def insert(
        self,
        collection: str,
        record: Record,
        record_id: Optional[RecordID] = None,
    ) -> RecordID:
        """Insert a new record."""
        self.validate_record(record)
        self._ensure_table_exists(collection)

        full_collection = self.get_full_collection_name(collection)
        conn = self._get_connection()

        # Generate or use provided ID
        if record_id is None:
            if "id" in record:
                record_id = record["id"]
            else:
                record_id = str(uuid.uuid4())

        # Add ID to record
        record = record.copy()
        record["id"] = record_id

        try:
            conn.execute(
                f"INSERT INTO {full_collection} (id, data) VALUES (?, ?)",
                (str(record_id), json.dumps(record)),
            )
            conn.commit()
            return record_id
        except sqlite3.IntegrityError:
            raise DuplicateRecordError(str(record_id), collection)
        except sqlite3.Error as e:
            raise OperationError(f"Failed to insert record: {e}")

    def insert_many(self, collection: str, records: List[Record]) -> List[RecordID]:
        """Insert multiple records."""
        inserted_ids = []
        conn = self._get_connection()

        try:
            for record in records:
                record_id = self.insert(collection, record)
                inserted_ids.append(record_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        return inserted_ids

    def fetch(self, collection: str, record_id: RecordID) -> Record:
        """Fetch a single record by ID."""
        full_collection = self.get_full_collection_name(collection)
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                f"SELECT data FROM {full_collection} WHERE id = ?",
                (str(record_id),),
            )
            row = cursor.fetchone()

            if row is None:
                raise RecordNotFoundError(str(record_id), collection)

            return json.loads(row["data"])
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                raise RecordNotFoundError(str(record_id), collection)
            raise OperationError(f"Failed to fetch record: {e}")

    def fetch_many(self, collection: str, record_ids: List[RecordID]) -> List[Record]:
        """Fetch multiple records by IDs."""
        full_collection = self.get_full_collection_name(collection)
        conn = self._get_connection()

        try:
            placeholders = ",".join("?" * len(record_ids))
            cursor = conn.execute(
                f"SELECT data FROM {full_collection} WHERE id IN ({placeholders})",
                [str(rid) for rid in record_ids],
            )

            records = []
            for row in cursor:
                records.append(json.loads(row["data"]))

            return records
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return []
            raise OperationError(f"Failed to fetch records: {e}")

    def update(
        self,
        collection: str,
        record_id: RecordID,
        updates: Dict[str, Any],
        upsert: bool = False,
    ) -> None:
        """Update an existing record."""
        try:
            # Fetch existing record
            record = self.fetch(collection, record_id)

            # Apply updates
            record.update(updates)

            # Save updated record
            full_collection = self.get_full_collection_name(collection)
            conn = self._get_connection()
            conn.execute(
                f"UPDATE {full_collection} SET data = ? WHERE id = ?",
                (json.dumps(record), str(record_id)),
            )
            conn.commit()

        except RecordNotFoundError:
            if upsert:
                # Insert new record
                new_record = updates.copy()
                new_record["id"] = record_id
                self.insert(collection, new_record, record_id)
            else:
                raise

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
        conn = self._get_connection()

        try:
            cursor = conn.execute(
                f"DELETE FROM {full_collection} WHERE id = ?",
                (str(record_id),),
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return False
            raise OperationError(f"Failed to delete record: {e}")

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
        try:
            self.fetch(collection, record_id)
            return True
        except RecordNotFoundError:
            return False

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
        conn = self._get_connection()

        try:
            # Build query
            query = f"SELECT data FROM {full_collection}"
            params = []

            # Note: For SQLite with JSON column, we fetch all and filter in Python
            # For better performance, consider using JSON functions in SQLite 3.38+

            cursor = conn.execute(query, params)

            records = []
            for row in cursor:
                record = json.loads(row["data"])

                # Apply filters
                if filters and not self._matches_filters(record, filters):
                    continue

                records.append(record)

            # Apply ordering
            if order_by:
                for field, direction in reversed(order_by):
                    reverse = direction.lower() == "desc"
                    records.sort(key=lambda x: x.get(field, ""), reverse=reverse)

            # Apply offset and limit
            if offset:
                records = records[offset:]
            if limit:
                records = records[:limit]

            return records

        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return []
            raise OperationError(f"Failed to query records: {e}")

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
        conn = self._get_connection()

        try:
            if filters is None:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {full_collection}")
                return cursor.fetchone()[0]
            else:
                # For filtered counts, we need to fetch and filter
                return len(self.query(collection, filters))

        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                return 0
            raise OperationError(f"Failed to count records: {e}")

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
        """List all collections/tables."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )

        collections = []
        for row in cursor:
            name = row["name"]
            if self._collection_prefix and name.startswith(self._collection_prefix):
                collections.append(name[len(self._collection_prefix) :])
            else:
                collections.append(name)

        return collections

    def collection_exists(self, collection: str) -> bool:
        """Check if collection/table exists."""
        full_collection = self.get_full_collection_name(collection)
        conn = self._get_connection()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (full_collection,),
        )
        return cursor.fetchone() is not None

    def create_collection(
        self,
        collection: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new collection/table."""
        full_collection = self.get_full_collection_name(collection)

        if self.collection_exists(collection):
            raise DuplicateRecordError(collection, "collection")

        conn = self._get_connection()
        conn.execute(f"""
            CREATE TABLE {full_collection} (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        conn.commit()

    def drop_collection(self, collection: str) -> None:
        """Drop a collection/table."""
        full_collection = self.get_full_collection_name(collection)

        if not self.collection_exists(collection):
            raise RecordNotFoundError(collection, "collection")

        conn = self._get_connection()
        conn.execute(f"DROP TABLE {full_collection}")
        conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        conn = self._get_connection()

        try:
            conn.execute("BEGIN")
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _matches_filters(self, record: Record, filters: QueryFilter) -> bool:
        """Check if record matches all filters."""
        for key, value in filters.items():
            record_value = self._get_nested_value(record, key)
            if record_value != value:
                return False
        return True

    def _get_nested_value(self, record: Record, key: str) -> Any:
        """Get value from nested dictionary using dot notation."""
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
