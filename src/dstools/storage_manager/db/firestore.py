"""
Google Firestore database storage implementation.

This implementation uses Google Firestore as the backend, providing serverless
NoSQL database storage with real-time capabilities.

Requires: google-cloud-firestore
"""

from typing import Dict, Any, List, Optional, Iterator, Tuple
from contextlib import contextmanager

from .base import BaseDBStorage, Record, RecordID, QueryFilter
from ..exceptions import DatabaseConnectionError, OperationError


class FirestoreDBStorage(BaseDBStorage):
    """
    Google Firestore database storage implementation.

    Features:
    - Serverless NoSQL database
    - Automatic scaling
    - Real-time synchronization
    - Offline support
    - Security rules

    Note: This implementation uses google-cloud-firestore which is
    already in the project dependencies.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Firestore storage.

        Args:
            config: Configuration dictionary with:
                - project_id: Google Cloud project ID
                - credentials_path: Path to service account JSON OR
                - credentials: Service account credentials dict
                - database_id: Database ID (default: "(default)")
                - emulator_host: Emulator host for development
        """
        super().__init__(config)

        try:
            from google.cloud import firestore
            self._firestore = firestore
        except ImportError:
            raise NotImplementedError(
                "Firestore storage requires google-cloud-firestore. "
                "Install with: pip install google-cloud-firestore"
            )

        self._project_id = config.get("project_id")
        self._credentials_path = config.get("credentials_path")
        self._credentials = config.get("credentials")
        self._database_id = config.get("database_id", "(default)")
        self._emulator_host = config.get("emulator_host")

        self._client = None
        self._connected = False

    def connect(self) -> None:
        """Establish connection to Firestore."""
        import os

        # Set emulator host if provided
        if self._emulator_host:
            os.environ["FIRESTORE_EMULATOR_HOST"] = self._emulator_host

        try:
            if self._credentials_path:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path
                )
                self._client = self._firestore.Client(
                    project=self._project_id,
                    credentials=credentials,
                    database=self._database_id,
                )
            elif self._credentials:
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_info(
                    self._credentials
                )
                self._client = self._firestore.Client(
                    project=self._project_id,
                    credentials=credentials,
                    database=self._database_id,
                )
            else:
                # Use default credentials
                self._client = self._firestore.Client(
                    project=self._project_id,
                    database=self._database_id,
                )

            self._connected = True
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to Firestore: {e}")

    def disconnect(self) -> None:
        """Close connection to Firestore."""
        if self._client:
            self._client = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._connected and self._client is not None

    def insert(
        self,
        collection: str,
        record: Record,
        record_id: Optional[RecordID] = None,
    ) -> RecordID:
        """Insert a new record."""
        raise NotImplementedError("Firestore implementation is a stub")

    def insert_many(self, collection: str, records: List[Record]) -> List[RecordID]:
        """Insert multiple records."""
        raise NotImplementedError("Firestore implementation is a stub")

    def fetch(self, collection: str, record_id: RecordID) -> Record:
        """Fetch a single record by ID."""
        raise NotImplementedError("Firestore implementation is a stub")

    def fetch_many(self, collection: str, record_ids: List[RecordID]) -> List[Record]:
        """Fetch multiple records by IDs."""
        raise NotImplementedError("Firestore implementation is a stub")

    def update(
        self,
        collection: str,
        record_id: RecordID,
        updates: Dict[str, Any],
        upsert: bool = False,
    ) -> None:
        """Update an existing record."""
        raise NotImplementedError("Firestore implementation is a stub")

    def update_many(
        self,
        collection: str,
        filters: QueryFilter,
        updates: Dict[str, Any],
    ) -> int:
        """Update multiple records matching filters."""
        raise NotImplementedError("Firestore implementation is a stub")

    def delete(self, collection: str, record_id: RecordID) -> bool:
        """Delete a record by ID."""
        raise NotImplementedError("Firestore implementation is a stub")

    def delete_many(self, collection: str, filters: QueryFilter) -> int:
        """Delete multiple records matching filters."""
        raise NotImplementedError("Firestore implementation is a stub")

    def exists(self, collection: str, record_id: RecordID) -> bool:
        """Check if a record exists."""
        raise NotImplementedError("Firestore implementation is a stub")

    def query(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Record]:
        """Query records with filters."""
        raise NotImplementedError("Firestore implementation is a stub")

    def query_one(
        self,
        collection: str,
        filters: QueryFilter,
    ) -> Optional[Record]:
        """Query for a single record."""
        raise NotImplementedError("Firestore implementation is a stub")

    def count(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
    ) -> int:
        """Count records matching filters."""
        raise NotImplementedError("Firestore implementation is a stub")

    def iterate(
        self,
        collection: str,
        filters: Optional[QueryFilter] = None,
        batch_size: int = 100,
    ) -> Iterator[Record]:
        """Iterate over records in batches."""
        raise NotImplementedError("Firestore implementation is a stub")

    def list_collections(self) -> List[str]:
        """List all collections."""
        raise NotImplementedError("Firestore implementation is a stub")

    def collection_exists(self, collection: str) -> bool:
        """Check if collection exists."""
        raise NotImplementedError("Firestore implementation is a stub")

    def create_collection(
        self,
        collection: str,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new collection."""
        # Firestore creates collections automatically
        pass

    def drop_collection(self, collection: str) -> None:
        """Drop a collection."""
        raise NotImplementedError("Firestore implementation is a stub")

    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        raise NotImplementedError("Firestore implementation is a stub")
