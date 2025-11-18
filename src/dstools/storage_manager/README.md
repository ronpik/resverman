# Storage Abstraction Layer

A comprehensive storage abstraction layer that provides unified interfaces for database storage (relational and NoSQL) and object storage systems.

## Features

- **Unified Interface**: Consistent API across different storage backends
- **Flexible Backends**: Support for multiple database and object store implementations
- **Development & Production**: Lightweight options for development, robust options for production
- **Type Safety**: Clear contracts and type hints
- **Integrated Operations**: Coordinate database records with object store items
- **Consistency Management**: Tools to maintain consistency between storage layers

## Quick Start

### Basic Usage

```python
from dstools.storage_manager import create_storage_manager

# Create storage manager for development/testing
manager = create_storage_manager(
    db_type="memory",
    object_store_type="filesystem_temp"
)

# Store an object with metadata
content = b"Hello, World!"
record_id = manager.store_object(
    content=content,
    object_key="files/hello.txt",
    metadata={"description": "Test file", "user_id": "user123"}
)

# Retrieve object
content, metadata = manager.fetch_object(record_id)
print(f"Content: {content.decode()}")
print(f"Metadata: {metadata}")

# Clean up
manager.close()
```

### Production Configuration

```python
from dstools.storage_manager import create_storage_manager

# Production setup with SQLite and persistent filesystem
manager = create_storage_manager(
    db_type="sqlite",
    db_config={
        "database_path": "/var/app/data.db",
        "journal_mode": "WAL"
    },
    object_store_type="filesystem_persistent",
    object_store_config={
        "base_path": "/var/app/storage",
        "enable_backups": True,
        "backup_path": "/var/app/backups"
    }
)
```

## Supported Storage Backends

### Database Storage

- **InMemoryDBStorage**: Fast in-memory storage for testing
- **SQLiteDBStorage**: File-based SQLite for local development
- **PostgreSQLDBStorage**: Production-grade relational database (stub)
- **MongoDBStorage**: NoSQL document database (stub)
- **FirestoreDBStorage**: Serverless NoSQL database (stub)

### Object Storage

- **TemporaryFilesystemObjectStore**: Temporary filesystem storage (auto-cleanup)
- **PersistentFilesystemObjectStore**: Persistent filesystem storage
- **FilesystemObjectStore**: Base filesystem storage
- **S3Storage**: AWS S3 object storage (stub)
- **MinIOStorage**: Self-hosted S3-compatible storage (stub)
- **DigitalOceanSpacesStorage**: DigitalOcean Spaces (stub)

## Examples

### Using Individual Storage Components

```python
from dstools.storage_manager import create_db_storage, create_object_store

# Database storage
db = create_db_storage("sqlite", database_path="app.db")
db.connect()

db.create_collection("users")
user_id = db.insert("users", {"name": "Alice", "email": "alice@example.com"})
user = db.fetch("users", user_id)

db.disconnect()

# Object storage
store = create_object_store("filesystem", base_path="./storage")
store.connect()

store.put("documents/file.pdf", pdf_content, content_type="application/pdf")
content = store.get("documents/file.pdf")

store.disconnect()
```

### Batch Operations

```python
manager = create_storage_manager(
    db_type="memory",
    object_store_type="filesystem_temp"
)

# Store multiple objects
objects = [
    ("docs/file1.pdf", pdf1_content, {"type": "document"}),
    ("docs/file2.pdf", pdf2_content, {"type": "document"}),
    ("images/photo.jpg", photo_content, {"type": "image"}),
]

results = manager.store_objects_batch(objects)

for result in results:
    if result["success"]:
        print(f"Stored: {result['record_id']}")
    else:
        print(f"Failed: {result['error']}")

manager.close()
```

### Querying and Listing

```python
manager = create_storage_manager(
    db_type="memory",
    object_store_type="filesystem_temp"
)

# Store some objects with metadata
manager.store_object(b"content1", "file1.txt", {"user_id": "user1", "type": "text"})
manager.store_object(b"content2", "file2.txt", {"user_id": "user1", "type": "text"})
manager.store_object(b"content3", "file3.bin", {"user_id": "user2", "type": "binary"})

# List all objects
all_objects = manager.list_objects()
print(f"Total objects: {len(all_objects)}")

# List with filters
user1_objects = manager.list_objects(filters={"user_id": "user1"})
print(f"User1 objects: {len(user1_objects)}")

# List text files
text_files = manager.list_objects(filters={"type": "text"})
print(f"Text files: {len(text_files)}")

manager.close()
```

### Consistency Management

```python
from dstools.storage_manager import check_consistency, repair_consistency

# Check consistency
report = manager._check_consistency()
print(f"Total records: {report['total_records']}")
print(f"Total objects: {report['total_objects']}")
print(f"Issues: {report['issues']}")

# Cleanup orphaned objects
stats = manager.cleanup_orphans()
print(f"Checked: {stats['checked']}")
print(f"Deleted: {stats['deleted']}")
```

## Configuration

### Database Storage Configuration

#### In-Memory Storage

```python
config = {
    "storage_type": "memory",
    "collections": ["users", "projects"],  # Pre-initialize collections
    "thread_safe": True
}
```

#### SQLite Storage

```python
config = {
    "storage_type": "sqlite",
    "database_path": "/path/to/database.db",
    "timeout": 5.0,
    "auto_create_tables": True,
    "journal_mode": "WAL"
}
```

### Object Store Configuration

#### Filesystem Storage

```python
config = {
    "storage_type": "filesystem",
    "base_path": "/path/to/storage",
    "create_base_path": True,
    "metadata_storage": "sidecar",  # or "memory"
    "file_permissions": "0644"
}
```

#### Temporary Filesystem Storage

```python
config = {
    "storage_type": "filesystem_temp",
    "cleanup_on_exit": True,
    "temp_dir": "/tmp/custom_temp"  # Optional
}
```

## Architecture

```
StorageManager
├── BaseDBStorage (abstract)
│   ├── InMemoryDBStorage
│   ├── SQLiteDBStorage
│   ├── PostgreSQLDBStorage (stub)
│   ├── MongoDBStorage (stub)
│   └── FirestoreDBStorage (stub)
│
└── BaseObjectStore (abstract)
    ├── FilesystemObjectStore
    │   ├── TemporaryFilesystemObjectStore
    │   └── PersistentFilesystemObjectStore
    └── S3ObjectStore (stubs)
        ├── S3Storage
        ├── MinIOStorage
        └── DigitalOceanSpacesStorage
```

## Exception Hierarchy

```
StorageException
├── ConfigurationError
│   ├── InvalidConfigurationError
│   └── MissingCredentialsError
├── ConnectionError
│   ├── DatabaseConnectionError
│   └── ObjectStoreConnectionError
├── OperationError
│   ├── RecordNotFoundError
│   ├── ObjectNotFoundError
│   ├── DuplicateRecordError
│   ├── ValidationError
│   └── ConsistencyError
├── ResourceError
│   ├── InsufficientStorageError
│   ├── QuotaExceededError
│   └── PermissionDeniedError
└── IntegrityError
    ├── ChecksumMismatchError
    └── PartialOperationError
```

## Testing

Run the basic tests:

```bash
python test_storage_manager.py
```

Or with pytest:

```bash
pytest src/dstools/storage_manager/tests/
```

## Future Enhancements

- Full implementations for PostgreSQL, MongoDB, Firestore
- Full implementations for S3, MinIO, DigitalOcean Spaces
- Additional database backends (Redis, DynamoDB, Cassandra)
- Additional object stores (Azure Blob, Google Cloud Storage)
- Built-in caching layer
- Query language abstraction
- Migration utilities
- Admin UI

## Contributing

This is part of the DSTools project. Contributions are welcome!

## License

MIT License
