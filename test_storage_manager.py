"""
Simple test runner for storage manager.
"""

import sys
sys.path.insert(0, 'src')

from dstools.storage_manager import (
    create_storage_manager,
    create_db_storage,
    create_object_store,
    RecordNotFoundError,
)

def test_memory_storage():
    """Test in-memory database storage."""
    print("Testing in-memory storage...")

    db = create_db_storage("memory")
    db.connect()

    # Create collection
    db.create_collection("test_collection")
    assert db.collection_exists("test_collection"), "Collection should exist"

    # Insert record
    record = {"name": "John", "age": 30}
    record_id = db.insert("test_collection", record)
    assert record_id is not None, "Record ID should not be None"

    # Fetch record
    fetched = db.fetch("test_collection", record_id)
    assert fetched["name"] == "John", "Name should match"
    assert fetched["age"] == 30, "Age should match"

    # Update record
    db.update("test_collection", record_id, {"age": 31})
    updated = db.fetch("test_collection", record_id)
    assert updated["age"] == 31, "Age should be updated"

    # Query
    db.insert("test_collection", {"name": "Alice", "age": 25})
    db.insert("test_collection", {"name": "Bob", "age": 25})
    results = db.query("test_collection", filters={"age": 25})
    assert len(results) == 2, "Should find 2 records with age 25"

    # Delete record
    assert db.delete("test_collection", record_id), "Delete should succeed"

    try:
        db.fetch("test_collection", record_id)
        assert False, "Should raise RecordNotFoundError"
    except RecordNotFoundError:
        pass  # Expected

    db.disconnect()
    print("✓ In-memory storage tests passed")


def test_sqlite_storage():
    """Test SQLite storage."""
    print("Testing SQLite storage...")

    import tempfile
    import os

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        db = create_db_storage("sqlite", database_path=db_path)
        db.connect()

        # Basic operations
        db.create_collection("test")
        record_id = db.insert("test", {"name": "Test", "value": 123})
        record = db.fetch("test", record_id)
        assert record["name"] == "Test", "Name should match"
        assert record["value"] == 123, "Value should match"

        db.disconnect()
        print("✓ SQLite storage tests passed")
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_filesystem_store():
    """Test filesystem object store."""
    print("Testing filesystem object store...")

    store = create_object_store("filesystem_temp")
    store.connect()

    # Put object
    content = b"Hello, World!"
    metadata = store.put("test.txt", content, content_type="text/plain")
    assert metadata.key == "test.txt", "Key should match"
    assert metadata.size_bytes == len(content), "Size should match"

    # Get object
    retrieved = store.get("test.txt")
    assert retrieved == content, "Content should match"

    # Check existence
    assert store.exists("test.txt"), "Object should exist"

    # List objects
    store.put("files/doc1.txt", b"content1")
    store.put("files/doc2.txt", b"content2")
    all_keys = store.list_objects()
    assert len(all_keys) == 3, "Should have 3 objects"

    # Delete object
    assert store.delete("test.txt"), "Delete should succeed"
    assert not store.exists("test.txt"), "Object should not exist"

    store.disconnect()
    print("✓ Filesystem store tests passed")


def test_storage_manager():
    """Test storage manager integration."""
    print("Testing storage manager...")

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
    assert record_id is not None, "Record ID should not be None"

    # Fetch object
    fetched_content, record = manager.fetch_object(record_id)
    assert fetched_content == content, "Content should match"
    assert record["description"] == "Test file", "Description should match"
    assert record["user_id"] == "user123", "User ID should match"

    # Update object
    content2 = b"Updated content"
    manager.update_object(record_id, content=content2)
    fetched_content, _ = manager.fetch_object(record_id)
    assert fetched_content == content2, "Updated content should match"

    # List objects
    manager.store_object(b"content1", "obj1.txt", {"type": "text"})
    manager.store_object(b"content2", "obj2.txt", {"type": "text"})
    all_objects = manager.list_objects()
    assert len(all_objects) == 3, "Should have 3 objects"

    # Batch operations
    objects = [
        ("batch1.txt", b"content1", {"index": 1}),
        ("batch2.txt", b"content2", {"index": 2}),
    ]
    results = manager.store_objects_batch(objects)
    assert len(results) == 2, "Should have 2 results"
    assert all(r["success"] for r in results), "All should succeed"

    # Delete object
    manager.delete_object(record_id)
    try:
        manager.fetch_object(record_id)
        assert False, "Should raise RecordNotFoundError"
    except RecordNotFoundError:
        pass  # Expected

    manager.close()
    print("✓ Storage manager tests passed")


if __name__ == "__main__":
    print("Running storage manager tests...\n")

    try:
        test_memory_storage()
        test_sqlite_storage()
        test_filesystem_store()
        test_storage_manager()

        print("\n✓ All tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
