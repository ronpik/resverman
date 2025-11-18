"""
Basic tests for storage manager.

These tests verify the core functionality of the storage manager
using in-memory storage and temporary filesystem storage.
"""

import pytest
from dstools.storage_manager import (
    create_storage_manager,
    create_db_storage,
    create_object_store,
    InMemoryDBStorage,
    TemporaryFilesystemObjectStore,
    RecordNotFoundError,
    ObjectNotFoundError,
)


class TestDBStorage:
    """Test database storage implementations."""

    def test_memory_storage_basic_operations(self):
        """Test basic operations with in-memory storage."""
        db = create_db_storage("memory")
        db.connect()

        # Create collection
        db.create_collection("test_collection")
        assert db.collection_exists("test_collection")

        # Insert record
        record = {"name": "John", "age": 30}
        record_id = db.insert("test_collection", record)
        assert record_id is not None

        # Fetch record
        fetched = db.fetch("test_collection", record_id)
        assert fetched["name"] == "John"
        assert fetched["age"] == 30

        # Update record
        db.update("test_collection", record_id, {"age": 31})
        updated = db.fetch("test_collection", record_id)
        assert updated["age"] == 31

        # Delete record
        assert db.delete("test_collection", record_id)
        with pytest.raises(RecordNotFoundError):
            db.fetch("test_collection", record_id)

        db.disconnect()

    def test_memory_storage_query(self):
        """Test query operations."""
        db = create_db_storage("memory")
        db.connect()

        db.create_collection("users")

        # Insert multiple records
        db.insert("users", {"name": "Alice", "age": 25, "city": "NYC"})
        db.insert("users", {"name": "Bob", "age": 30, "city": "LA"})
        db.insert("users", {"name": "Charlie", "age": 25, "city": "NYC"})

        # Query by field
        results = db.query("users", filters={"age": 25})
        assert len(results) == 2

        # Query with limit
        results = db.query("users", limit=2)
        assert len(results) == 2

        # Count
        count = db.count("users")
        assert count == 3

        db.disconnect()


class TestObjectStore:
    """Test object store implementations."""

    def test_filesystem_store_basic_operations(self):
        """Test basic operations with filesystem storage."""
        store = create_object_store("filesystem_temp")
        store.connect()

        # Put object
        content = b"Hello, World!"
        metadata = store.put("test.txt", content, content_type="text/plain")
        assert metadata.key == "test.txt"
        assert metadata.size_bytes == len(content)

        # Get object
        retrieved = store.get("test.txt")
        assert retrieved == content

        # Check existence
        assert store.exists("test.txt")

        # Get metadata
        obj_metadata = store.get_metadata("test.txt")
        assert obj_metadata.key == "test.txt"

        # Delete object
        assert store.delete("test.txt")
        assert not store.exists("test.txt")

        store.disconnect()

    def test_filesystem_store_listing(self):
        """Test listing operations."""
        store = create_object_store("filesystem_temp")
        store.connect()

        # Put multiple objects
        store.put("files/doc1.txt", b"content1")
        store.put("files/doc2.txt", b"content2")
        store.put("images/photo.jpg", b"photo data")

        # List all objects
        all_keys = store.list_objects()
        assert len(all_keys) == 3

        # List with prefix
        file_keys = store.list_objects(prefix="files/")
        assert len(file_keys) == 2

        store.disconnect()


class TestStorageManager:
    """Test storage manager integration."""

    def test_store_and_fetch_object(self):
        """Test storing and fetching object with metadata."""
        manager = create_storage_manager(
            db_type="memory",
            object_store_type="filesystem_temp",
        )

        # Store object
        content = b"Test file content"
        record_id = manager.store_object(
            content=content,
            object_key="test/file.txt",
            metadata={"description": "Test file", "user_id": "user123"},
        )

        assert record_id is not None

        # Fetch object
        fetched_content, record = manager.fetch_object(record_id)
        assert fetched_content == content
        assert record["description"] == "Test file"
        assert record["user_id"] == "user123"

        manager.close()

    def test_update_object(self):
        """Test updating object content."""
        manager = create_storage_manager(
            db_type="memory",
            object_store_type="filesystem_temp",
        )

        # Store initial object
        content1 = b"Original content"
        record_id = manager.store_object(
            content=content1,
            object_key="test/update.txt",
        )

        # Update object
        content2 = b"Updated content"
        manager.update_object(record_id, content=content2)

        # Fetch updated object
        fetched_content, record = manager.fetch_object(record_id)
        assert fetched_content == content2

        manager.close()

    def test_delete_object(self):
        """Test deleting object and record."""
        manager = create_storage_manager(
            db_type="memory",
            object_store_type="filesystem_temp",
        )

        # Store object
        content = b"Delete me"
        record_id = manager.store_object(
            content=content,
            object_key="test/delete.txt",
        )

        # Delete object
        manager.delete_object(record_id)

        # Verify deletion
        with pytest.raises(RecordNotFoundError):
            manager.fetch_object(record_id)

        manager.close()

    def test_list_objects(self):
        """Test listing objects."""
        manager = create_storage_manager(
            db_type="memory",
            object_store_type="filesystem_temp",
        )

        # Store multiple objects
        manager.store_object(b"content1", "obj1.txt", {"type": "text"})
        manager.store_object(b"content2", "obj2.txt", {"type": "text"})
        manager.store_object(b"content3", "obj3.txt", {"type": "binary"})

        # List all objects
        all_objects = manager.list_objects()
        assert len(all_objects) == 3

        # List with filter
        text_objects = manager.list_objects(filters={"type": "text"})
        assert len(text_objects) == 2

        manager.close()

    def test_batch_operations(self):
        """Test batch store operations."""
        manager = create_storage_manager(
            db_type="memory",
            object_store_type="filesystem_temp",
        )

        # Store multiple objects
        objects = [
            ("batch1.txt", b"content1", {"index": 1}),
            ("batch2.txt", b"content2", {"index": 2}),
            ("batch3.txt", b"content3", {"index": 3}),
        ]

        results = manager.store_objects_batch(objects)
        assert len(results) == 3
        assert all(r["success"] for r in results)

        manager.close()


def test_sqlite_storage():
    """Test SQLite storage."""
    import tempfile
    import os

    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        db = create_db_storage("sqlite", database_path=db_path)
        db.connect()

        # Basic operations
        db.create_collection("test")
        record_id = db.insert("test", {"name": "Test"})
        record = db.fetch("test", record_id)
        assert record["name"] == "Test"

        db.disconnect()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    # Run basic smoke tests
    print("Running basic smoke tests...")

    test_db = TestDBStorage()
    test_db.test_memory_storage_basic_operations()
    print("✓ Memory storage basic operations")

    test_db.test_memory_storage_query()
    print("✓ Memory storage query operations")

    test_store = TestObjectStore()
    test_store.test_filesystem_store_basic_operations()
    print("✓ Filesystem store basic operations")

    test_store.test_filesystem_store_listing()
    print("✓ Filesystem store listing operations")

    test_manager = TestStorageManager()
    test_manager.test_store_and_fetch_object()
    print("✓ Storage manager store and fetch")

    test_manager.test_update_object()
    print("✓ Storage manager update")

    test_manager.test_delete_object()
    print("✓ Storage manager delete")

    test_manager.test_list_objects()
    print("✓ Storage manager list")

    test_manager.test_batch_operations()
    print("✓ Storage manager batch operations")

    test_sqlite_storage()
    print("✓ SQLite storage")

    print("\nAll tests passed! ✓")
