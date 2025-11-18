# DSTools Comprehensive Documentation

This document provides detailed information about each utility in the DSTools package, including usage examples, use cases, and best practices.

## Table of Contents

1. [Common Utilities](#common-utilities)
   - [Time Measurement](#time-measurement)
   - [JSON I/O](#json-io)
   - [I/O Utilities](#io-utilities)
   - [Async I/O Utilities](#async-io-utilities)
   - [Iterator Utilities](#iterator-utilities)
   - [Async Iterator Utilities](#async-iterator-utilities)
   - [Image Utilities](#image-utilities)
2. [Storage Handlers](#storage-handlers)
3. [Compression](#compression)
4. [Resource Management](#resource-management)
5. [Reporting](#reporting)
6. [Data Management](#data-management)

---

## Common Utilities

### Time Measurement

**Module**: `dstools.common.time_measure`

The `DurationMeasure` context manager provides accurate execution time measurement with automatic unit adjustment.

#### Features

- Context manager for measuring code execution time
- Automatic unit fallback (seconds → milliseconds → microseconds → nanoseconds)
- Logging integration with customizable log levels
- Can be used as a decorator or context manager

#### API Reference

```python
class DurationMeasure:
    def __init__(
        self,
        action: str,
        logger: Optional[LoggerType] = None,
        log_start: bool = False,
        log_end: bool = True,
        log_level: int = LoggerLevel.INFO,
        unit: TimeUnit = TimeUnit.MILLISECONDS,
        fallback: bool = True
    )
```

**Parameters**:
- `action`: Description of the measured action
- `logger`: Custom logger instance (uses globalog.LOG by default)
- `log_start`: Whether to log when measurement starts
- `log_end`: Whether to log when measurement completes
- `log_level`: Logging level for messages
- `unit`: Desired time unit (SECONDS, MILLISECONDS, MICROSECONDS, NANOSECONDS)
- `fallback`: Whether to automatically adjust to smaller units if duration is 0

#### Examples

**Basic Usage**:
```python
from dstools.common.time_measure import DurationMeasure, TimeUnit

with DurationMeasure(action='data processing'):
    # Your code here
    process_data()
# Output: "Completed: data processing (duration: 150.2345ms, total: 0.15s)"
```

**Access Duration Programmatically**:
```python
with DurationMeasure(action='model training', unit=TimeUnit.SECONDS) as dm:
    train_model()

print(f"Training took {dm.duration:.2f} seconds")
```

**As a Decorator**:
```python
@DurationMeasure(action='API request')
def fetch_data_from_api():
    return requests.get('https://api.example.com/data')

result = fetch_data_from_api()
```

**With Custom Logging**:
```python
from globalog import LOG

with DurationMeasure(
    action='database query',
    logger=LOG,
    log_start=True,
    log_level=LoggerLevel.DEBUG,
    unit=TimeUnit.MILLISECONDS
):
    execute_query()
```

#### Use Cases

1. **Performance Monitoring**: Track execution time of critical code paths
2. **Benchmarking**: Compare performance of different implementations
3. **Debugging**: Identify performance bottlenecks
4. **Logging**: Automatically log operation durations with context
5. **API Monitoring**: Measure response times for external API calls

---

### JSON I/O

**Module**: `dstools.common.json_io`

Simple, consistent interface for JSON and JSONL (JSON Lines) file operations.

#### API Reference

```python
def write_json(data: JSON, path: str) -> None
def read_json(path: str | Path) -> JSON
def write_json_lines(path: str | Path, data: Iterable[JSON]) -> None
def read_json_lines(path: str | Path) -> Iterator[JSON]
```

#### Examples

**Basic JSON Operations**:
```python
from dstools.common.json_io import write_json, read_json

# Save configuration
config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000
}
write_json(config, "config.json")

# Load configuration
loaded_config = read_json("config.json")
```

**JSONL for Large Datasets**:
```python
from dstools.common.json_io import write_json_lines, read_json_lines

# Write streaming data
def generate_records():
    for i in range(1000000):
        yield {"id": i, "value": i * 2}

write_json_lines("large_dataset.jsonl", generate_records())

# Read streaming data (memory efficient)
for record in read_json_lines("large_dataset.jsonl"):
    process_record(record)
```

**Processing Log Files**:
```python
# Read and filter logs
errors = [
    log for log in read_json_lines("application.log")
    if log.get("level") == "ERROR"
]

# Write filtered results
write_json_lines("errors.jsonl", errors)
```

#### Use Cases

1. **Configuration Files**: Store and load application configurations
2. **Data Export/Import**: Exchange data between systems
3. **Log Processing**: Handle structured log files (JSONL format)
4. **Data Pipelines**: Stream large datasets without loading into memory
5. **Model Checkpoints**: Save and load model metadata

---

### I/O Utilities

**Module**: `dstools.common.io_utils`

Basic synchronous file I/O operations for text and binary data.

#### API Reference

```python
def write_text(path: str | Path, content: str) -> None
def read_text(path: str | Path) -> str
def write_bytes(path: str | Path, content: bytes) -> None
def read_bytes(path: str | Path) -> bytes
def write_lines(path: str | Path, lines: Iterable[str]) -> None
def read_lines(path: str | Path) -> Iterator[str]
```

#### Examples

**Text File Operations**:
```python
from dstools.common.io_utils import write_text, read_text

# Write text
write_text("output.txt", "Hello, World!\nThis is a test.")

# Read text
content = read_text("output.txt")
```

**Binary File Operations**:
```python
from dstools.common.io_utils import write_bytes, read_bytes

# Save binary data
data = bytes([0x89, 0x50, 0x4E, 0x47])  # PNG header
write_bytes("data.bin", data)

# Load binary data
loaded = read_bytes("data.bin")
```

**Line-by-Line Processing**:
```python
from dstools.common.io_utils import write_lines, read_lines

# Write lines
lines = ["Line 1", "Line 2", "Line 3"]
write_lines("output.txt", lines)

# Read lines (memory efficient for large files)
for line in read_lines("large_file.txt"):
    if "ERROR" in line:
        print(line)
```

**Generator-Based Writing**:
```python
def generate_lines():
    for i in range(1000000):
        yield f"Line {i}: Some data"

# Memory-efficient writing
write_lines("huge_file.txt", generate_lines())
```

#### Use Cases

1. **Log Processing**: Read and filter large log files line by line
2. **Text Analysis**: Process text files without loading entirely into memory
3. **Binary Data**: Handle binary file formats
4. **Data Export**: Generate and write large text files efficiently
5. **Configuration Management**: Read/write simple text-based configs

---

### Async I/O Utilities

**Module**: `dstools.common.aio_utils`

Asynchronous file I/O operations using `aiofiles` for high-performance concurrent operations.

#### API Reference

```python
async def write_text(path: Union[str, Path], content: str) -> None
async def read_text(path: Union[str, Path]) -> str
async def write_bytes(path: Union[str, Path], content: bytes) -> int
async def read_bytes(path: Union[str, Path]) -> bytes
async def write_lines(path: Union[str, Path], lines: Iterable[str]) -> None
async def read_lines(path: Union[str, Path]) -> AsyncIterator[str]
```

#### Examples

**Basic Async Operations**:
```python
import asyncio
from dstools.common.aio_utils import write_text, read_text

async def main():
    # Write asynchronously
    await write_text("async_file.txt", "Async content")

    # Read asynchronously
    content = await read_text("async_file.txt")
    print(content)

asyncio.run(main())
```

**Concurrent File Operations**:
```python
import asyncio
from dstools.common.aio_utils import write_text, read_text

async def process_files():
    # Process multiple files concurrently
    tasks = [
        write_text(f"file_{i}.txt", f"Content {i}")
        for i in range(100)
    ]
    await asyncio.gather(*tasks)

    # Read multiple files concurrently
    read_tasks = [read_text(f"file_{i}.txt") for i in range(100)]
    results = await asyncio.gather(*read_tasks)
    return results

asyncio.run(process_files())
```

**Async Line Streaming**:
```python
from dstools.common.aio_utils import read_lines, write_lines

async def filter_large_file():
    filtered_lines = []
    async for line in read_lines("large_input.txt"):
        if "important" in line.lower():
            filtered_lines.append(line)

    await write_lines("filtered_output.txt", filtered_lines)

asyncio.run(filter_large_file())
```

**Download and Save Multiple Resources**:
```python
import aiohttp
from dstools.common.aio_utils import write_bytes

async def download_resources(urls):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, url in enumerate(urls):
            async def fetch_and_save(url, index):
                async with session.get(url) as response:
                    content = await response.read()
                    await write_bytes(f"resource_{index}.bin", content)
            tasks.append(fetch_and_save(url, i))

        await asyncio.gather(*tasks)

urls = ["http://example.com/file1", "http://example.com/file2"]
asyncio.run(download_resources(urls))
```

#### Use Cases

1. **Web Scraping**: Download and save multiple files concurrently
2. **API Integration**: Process API responses asynchronously
3. **Batch Processing**: Handle large numbers of files concurrently
4. **Real-time Systems**: Non-blocking file operations in async applications
5. **Data Pipelines**: Async ETL processes with concurrent I/O

---

### Iterator Utilities

**Module**: `dstools.common.iter_utils`

A comprehensive collection of iterator manipulation and transformation utilities.

#### API Reference

Key functions:
```python
def chunked(iterable: Iterable[T], chunk_size: int) -> Generator[List[T], None, None]
def merge_iters(*iterables: Iterable[T], key: Callable[[T], CT]) -> Iterable[T]
def make_unique(iterable: Iterable[T]) -> Iterable[T]
def partition(predicate: Callable[[T], bool], iterable: Iterable[T]) -> Tuple[List[T], List[T]]
def zip_with_next(iterable: Iterable[T], extra_last_pair: bool = False) -> Iterator[Tuple[T, T]]
def take_first(seq: Sequence[T], default_value: Optional[T] = None) -> Optional[T]
def on_each(op: Callable[[T], Any], iterable: Iterable[T]) -> Iterator[T]
def argmax(seq: Sequence[T], key: Optional[Callable[[T], CT]] = None) -> int
```

#### Examples

**Chunking Data**:
```python
from dstools.common.iter_utils import chunked

# Process data in batches
data = range(1000)
for batch in chunked(data, chunk_size=50):
    # Process 50 items at a time
    insert_to_database(batch)

# API requests with batching
user_ids = get_user_ids()
for user_batch in chunked(user_ids, chunk_size=100):
    response = api.get_users(user_batch)
```

**Merging Sorted Iterables**:
```python
from dstools.common.iter_utils import merge_iters

# Merge sorted logs from multiple sources
log_files = [
    read_json_lines("server1.log"),
    read_json_lines("server2.log"),
    read_json_lines("server3.log")
]

# Merge by timestamp
merged_logs = merge_iters(*log_files, key=lambda log: log['timestamp'])
for log in merged_logs:
    process_log(log)
```

**Removing Duplicates**:
```python
from dstools.common.iter_utils import make_unique

# Remove duplicates while preserving order
user_ids = [1, 2, 3, 2, 4, 1, 5, 3]
unique_ids = list(make_unique(user_ids))  # [1, 2, 3, 4, 5]

# Process unique items from a stream
for unique_item in make_unique(data_stream()):
    process(unique_item)
```

**Partitioning Data**:
```python
from dstools.common.iter_utils import partition

# Split data by condition
numbers = range(1, 11)
evens, odds = partition(lambda x: x % 2 == 0, numbers)
# evens: [2, 4, 6, 8, 10], odds: [1, 3, 5, 7, 9]

# Separate valid and invalid records
valid, invalid = partition(
    lambda record: record.is_valid(),
    records
)
write_json_lines("valid.jsonl", valid)
write_json_lines("invalid.jsonl", invalid)
```

**Zip with Next**:
```python
from dstools.common.iter_utils import zip_with_next

# Process consecutive pairs
prices = [100, 105, 103, 108, 110]
for current, next_price in zip_with_next(prices):
    change = next_price - current
    print(f"Change: {change:+.2f}")

# Detect transitions
states = ['idle', 'running', 'running', 'stopped', 'running']
for state, next_state in zip_with_next(states):
    if state != next_state:
        print(f"Transition: {state} → {next_state}")
```

**Side Effects with on_each**:
```python
from dstools.common.iter_utils import on_each

# Log each item while processing
def log_item(item):
    LOG.info(f"Processing {item}")

result = list(
    on_each(log_item, data_stream())
)

# Count items while filtering
counter = {'count': 0}
def increment(item):
    counter['count'] += 1

filtered = [
    x for x in on_each(increment, data)
    if x > 10
]
print(f"Processed {counter['count']} items, filtered to {len(filtered)}")
```

**Finding Maximum Index**:
```python
from dstools.common.iter_utils import argmax

scores = [0.7, 0.9, 0.8, 0.95, 0.6]
best_idx = argmax(scores)  # 3

# With custom key
people = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 45},
    {"name": "Charlie", "age": 35}
]
oldest_idx = argmax(people, key=lambda p: p['age'])  # 1
```

#### Use Cases

1. **Batch Processing**: Process large datasets in chunks
2. **Data Merging**: Merge multiple sorted data streams
3. **Deduplication**: Remove duplicates from data streams
4. **Data Validation**: Separate valid/invalid records
5. **Time Series Analysis**: Process consecutive data points
6. **Stream Processing**: Transform data streams efficiently
7. **Performance Optimization**: Lazy evaluation for memory efficiency

---

### Async Iterator Utilities

**Module**: `dstools.common.async_iter_utils`

Asynchronous iterator utilities for working with async iterables.

#### API Reference

```python
async def async_chunked(
    iterable: AsyncIterable[T],
    chunk_size: int
) -> AsyncGenerator[List[T], None]
```

#### Examples

**Async Chunking**:
```python
from dstools.common.async_iter_utils import async_chunked

async def process_stream():
    async def data_stream():
        for i in range(1000):
            yield {"id": i, "value": i * 2}

    async for chunk in async_chunked(data_stream(), chunk_size=50):
        # Process 50 items at a time
        await batch_insert(chunk)

asyncio.run(process_stream())
```

**API Pagination**:
```python
async def fetch_all_pages(api_client):
    async def page_generator():
        page = 1
        while True:
            results = await api_client.get_page(page)
            if not results:
                break
            for item in results:
                yield item
            page += 1

    # Process in batches of 100
    async for batch in async_chunked(page_generator(), chunk_size=100):
        await process_batch(batch)
```

#### Use Cases

1. **Async Batch Processing**: Process async data streams in batches
2. **API Pagination**: Fetch and process paginated API results
3. **Database Operations**: Bulk inserts from async data sources
4. **Stream Processing**: Handle async data streams efficiently

---

### Image Utilities

**Module**: `dstools.common.image_utils`

Utilities for image I/O, conversion, and validation using PIL.

#### API Reference

```python
# image_io.py
def image_to_bytes(image: Image, format: Optional[str] = None) -> bytes
async def image_to_bytes_async(image: Image, format: Optional[str] = None) -> bytes
def image_from_bytes(content: bytes) -> Image
def store_image(image: Image, path: Path, format: Optional[str] = None) -> Path
async def store_image_async(image: Image, path: Path, format: Optional[str] = None) -> Path

# image_pixels.py
def image_to_numpy(image: Image) -> np.ndarray
def numpy_to_image(array: np.ndarray) -> Image

# image_validation.py
def validate_image(image: Image, min_size: Tuple[int, int]) -> bool
```

Supported formats: `png`, `tif`, `tiff`, `jpg`, `jpeg`

#### Examples

**Image Format Conversion**:
```python
from PIL import Image
from dstools.common.image_utils import image_to_bytes, image_from_bytes, store_image
from pathlib import Path

# Load image
image = Image.open("input.png")

# Convert to bytes
jpeg_bytes = image_to_bytes(image, format='jpeg')

# Save in different format
store_image(image, Path("output.jpg"), format='jpg')

# Load from bytes
reconstructed = image_from_bytes(jpeg_bytes)
```

**Async Image Processing**:
```python
import asyncio
from dstools.common.image_utils import store_image_async

async def save_images(images, output_dir):
    tasks = [
        store_image_async(img, Path(output_dir) / f"image_{i}.png")
        for i, img in enumerate(images)
    ]
    await asyncio.gather(*tasks)

asyncio.run(save_images(image_list, "output"))
```

**Working with NumPy**:
```python
from dstools.common.image_utils.image_pixels import image_to_numpy, numpy_to_image
import numpy as np

# Convert to numpy for processing
img_array = image_to_numpy(image)

# Image processing
processed = np.clip(img_array * 1.2, 0, 255).astype(np.uint8)

# Convert back to PIL Image
result_image = numpy_to_image(processed)
```

**Batch Image Processing**:
```python
from pathlib import Path
from PIL import Image
from dstools.common.image_utils import store_image

def resize_images(input_dir, output_dir, size=(800, 600)):
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for img_file in input_path.glob("*.jpg"):
        image = Image.open(img_file)
        resized = image.resize(size, Image.LANCZOS)
        store_image(resized, output_path / img_file.name, format='jpg')
```

#### Use Cases

1. **Format Conversion**: Convert images between different formats
2. **Image Processing**: Integration with NumPy for advanced processing
3. **Thumbnail Generation**: Batch resize images
4. **Web APIs**: Convert images to bytes for API transmission
5. **Data Pipelines**: Process images in ML data pipelines

---

## Storage Handlers

**Module**: `dstools.storage.handlers`

Unified interface for multiple storage backends (Local, GCS, S3, SSH).

### Storage Handler Factory

```python
from dstools.storage.handlers.storage_handler import StorageHandlerFactory

handler = StorageHandlerFactory.get_handler(storage_type: str, storage_config: dict)
```

All handlers implement the `StorageHandler` interface:
```python
class StorageHandler(ABC):
    def download(self, remote_relative_path: str) -> bytes
    def upload(self, compressed_data: bytes, remote_relative_path: str) -> bool
```

### Local Storage

**Configuration**:
```python
config = {'root_dir': Path('/path/to/storage')}
handler = StorageHandlerFactory.get_handler('LOCAL', config)
```

**Example**:
```python
from dstools.storage.handlers.storage_handler import StorageHandlerFactory
from pathlib import Path

# Initialize
config = {'root_dir': Path.home() / 'data' / 'storage'}
local = StorageHandlerFactory.get_handler('LOCAL', config)

# Upload
local.upload(b'file content', 'project/data.bin')

# Download
content = local.download('project/data.bin')
```

### Google Cloud Storage (GCS)

**Configuration**:
```python
config = {
    'bucket': 'my-bucket-name',
    'credentials_path': 'path/to/service-account.json'
}
handler = StorageHandlerFactory.get_handler('GCS', config)
```

**Example**:
```python
from dstools.storage.handlers.storage_handler import StorageHandlerFactory

# Initialize
config = {
    'bucket': 'my-ml-datasets',
    'credentials_path': '/home/user/.gcp/credentials.json'
}
gcs = StorageHandlerFactory.get_handler('GCS', config)

# Upload file
with open('model.pkl', 'rb') as f:
    gcs.upload(f.read(), 'models/v1/model.pkl')

# Download file
model_data = gcs.download('models/v1/model.pkl')

# GCS-specific methods
if gcs.exists('models/v1/model.pkl'):
    size = gcs.size('models/v1/model.pkl')
    print(f"Model size: {size} bytes")

# List objects
for blob in gcs.list_objects(prefix='models/'):
    print(f"Found: {blob.name}")
```

### S3 Storage

**Configuration**:
```python
config = {
    'bucket': 'my-s3-bucket',
    'aws_access_key_id': 'YOUR_ACCESS_KEY',
    'aws_secret_access_key': 'YOUR_SECRET_KEY',
    'region': 'us-east-1'
}
handler = StorageHandlerFactory.get_handler('S3', config)
```

### SSH Storage

**Configuration**:
```python
config = {
    'hostname': 'remote.server.com',
    'username': 'user',
    'key_path': '~/.ssh/id_rsa',
    'remote_path': '/data/storage'
}
handler = StorageHandlerFactory.get_handler('SSH', config)
```

### Use Cases

1. **Multi-Cloud Strategy**: Abstract storage backend for portability
2. **Development/Production Parity**: Use local storage in dev, cloud in production
3. **Data Backup**: Store backups across multiple storage backends
4. **Data Migration**: Easily migrate data between storage systems
5. **Hybrid Cloud**: Combine on-premise and cloud storage

### Best Practices

1. **Configuration Management**: Store credentials securely, use environment variables
2. **Error Handling**: Always handle upload/download failures
3. **Retry Logic**: Implement retries for network operations
4. **Compression**: Compress data before upload to reduce costs and improve speed
5. **Logging**: Log all storage operations for auditing

---

## Compression

**Module**: `dstools.compression`

Compression utilities for bytes and folder compression using Snappy and tar.

### Snappy Compressor

**Module**: `dstools.compression.snappy_compressor`

Fast compression/decompression using the Snappy algorithm.

```python
from dstools.compression.snappy_compressor import SnappyCompressor

compressor = SnappyCompressor()
compressed = compressor.compress(data: bytes) -> bytes
decompressed = compressor.decompress(data: bytes) -> bytes
```

**Example**:
```python
from dstools.compression.snappy_compressor import SnappyCompressor
import json

compressor = SnappyCompressor()

# Compress JSON data
data = {"large": "dataset", "records": [1, 2, 3] * 1000}
json_bytes = json.dumps(data).encode()
compressed = compressor.compress(json_bytes)

print(f"Original: {len(json_bytes)} bytes")
print(f"Compressed: {len(compressed)} bytes")
print(f"Ratio: {len(compressed)/len(json_bytes)*100:.1f}%")

# Decompress
decompressed = compressor.decompress(compressed)
loaded_data = json.loads(decompressed.decode())
```

### Folder Compressor

**Module**: `dstools.compression.folder_compress`

Compress entire folders into bytes using tar + Snappy compression.

```python
from dstools.compression.folder_compress import FolderCompressor
from dstools.compression.snappy_compressor import SnappyCompressor

compressor = FolderCompressor(
    bytes_compressor: Compressor,
    mode: Optional[Literal['gz', 'bz2', 'xz']] = None
)
```

**Methods**:
- `compress_folder(folder_path: Path) -> bytes`
- `decompress_to_folder(data: bytes, destination_folder: Path)`

**Example**:
```python
from dstools.compression.folder_compress import FolderCompressor
from dstools.compression.snappy_compressor import SnappyCompressor
from pathlib import Path

# Initialize
bytes_compressor = SnappyCompressor()
folder_compressor = FolderCompressor(bytes_compressor, mode='gz')

# Compress a folder
model_dir = Path('trained_models/v1')
compressed_data = folder_compressor.compress_folder(model_dir)

# Save compressed data
with open('model_v1.tar.gz.snappy', 'wb') as f:
    f.write(compressed_data)

# Decompress to a new location
with open('model_v1.tar.gz.snappy', 'rb') as f:
    compressed_data = f.read()

output_dir = Path('restored_models')
folder_compressor.decompress_to_folder(compressed_data, output_dir)
```

**Compression Modes**:
- `'gz'`: gzip (good balance of speed and compression)
- `'bz2'`: bzip2 (better compression, slower)
- `'xz'`: LZMA (best compression, slowest)
- `None`: No tar compression (only Snappy)

### Use Cases

1. **Model Serialization**: Compress ML models for storage/transfer
2. **Dataset Archiving**: Archive large datasets efficiently
3. **Backup Systems**: Compress folders before backup
4. **Resource Distribution**: Distribute application resources
5. **Network Transfer**: Reduce bandwidth usage

### Performance Comparison

```python
import time
from pathlib import Path
from dstools.compression.folder_compress import FolderCompressor
from dstools.compression.snappy_compressor import SnappyCompressor

compressor = SnappyCompressor()
modes = ['gz', 'bz2', 'xz', None]

for mode in modes:
    fc = FolderCompressor(compressor, mode=mode)

    start = time.time()
    compressed = fc.compress_folder(Path('test_folder'))
    compress_time = time.time() - start

    print(f"Mode: {mode or 'snappy-only'}")
    print(f"  Size: {len(compressed):,} bytes")
    print(f"  Time: {compress_time:.2f}s")
```

---

## Resource Management

**Module**: `dstools.resource_management`

Version-controlled resource management system with automatic download/upload and caching.

### Core Concepts

- **Resource**: Versioned data asset (dataset, model, configuration)
- **Local Storage**: Cached resources on local filesystem
- **Remote Storage**: Cloud storage for resource distribution
- **Automatic Sync**: Downloads resources on first use, caches locally

### Resource Class

**Base Class**:
```python
from dstools.resource_management.resource import Resource

class MyResource(Resource, resource_name='my_resource', version='1.0'):
    def __init__(self):
        super().__init__()
        # Define resource files
        self.data_file = self.local_path / 'data.csv'

    def get_data(self):
        # Access resource files
        with open(self.data_file) as f:
            return f.read()
```

**Attributes**:
- `name`: Resource name
- `version`: Resource version
- `local_path`: Path to local cache
- `remote_relative_path`: Path in remote storage

**Methods**:
- `load()`: Download resource if not cached locally
- `upload()`: Upload resource to remote storage

### Configuration

**Config File**: `~/.dstools/rvs.json` or project-specific location

```json
{
  "resources_root": "~/.dstools/resources",
  "remote_root": "resources",
  "storage": {
    "remote_storage_type": "GCS",
    "storage_config": {
      "bucket": "my-resources-bucket",
      "credentials_path": "/path/to/credentials.json"
    }
  }
}
```

**Configuration Class**:
```python
from dstools.resource_management.resource_config import ResourceConfig

# Load from file
config = ResourceConfig.from_path(Path('rvs.json'))

# Access configuration
print(config.resources_root)
print(config.remote_storage_type)
```

### Examples

**Simple Resource**:
```python
from dstools.resource_management.resource import Resource
from pathlib import Path

class StopwordsResource(Resource, resource_name='stopwords', version='1.0'):
    def __init__(self):
        super().__init__()
        self.stopwords_file = self.local_path / 'stopwords.txt'

    def get_stopwords(self) -> set:
        with open(self.stopwords_file) as f:
            return set(line.strip() for line in f)

# Usage (automatically downloads if needed)
stopwords = StopwordsResource()
words = stopwords.get_stopwords()
```

**ML Model Resource**:
```python
import pickle
from dstools.resource_management.resource import Resource

class ModelResource(Resource, resource_name='sentiment_model', version='2.1'):
    def __init__(self):
        super().__init__()
        self.model_file = self.local_path / 'model.pkl'
        self.config_file = self.local_path / 'config.json'

    def load_model(self):
        with open(self.model_file, 'rb') as f:
            return pickle.load(f)

    def get_config(self):
        from dstools.common.json_io import read_json
        return read_json(self.config_file)

# Singleton pattern - same instance returned
model_resource = ModelResource()
model = model_resource.load_model()
config = model_resource.get_config()
```

**Uploading New Version**:
```python
from pathlib import Path
from dstools.resource_management.resource import Resource

class DatasetResource(Resource, resource_name='training_data', version='3.0'):
    def __init__(self):
        super().__init__()

# Prepare resource locally
resource = DatasetResource()
resource_path = resource.local_path
resource_path.mkdir(parents=True, exist_ok=True)

# Add files to resource
prepare_dataset(resource_path)

# Upload to remote storage
resource.upload()
```

**Multiple Versions**:
```python
class DataV1(Resource, resource_name='dataset', version='1.0'):
    pass

class DataV2(Resource, resource_name='dataset', version='2.0'):
    pass

# Use different versions
data_v1 = DataV1()
data_v2 = DataV2()
```

### Resource Structure

When stored, resources are compressed into a single file:

```
Local: ~/.dstools/resources/
  ├── sentiment_model/
  │   └── V2.1/
  │       ├── model.pkl
  │       └── config.json
  └── training_data/
      └── V3.0/
          ├── train.csv
          ├── test.csv
          └── metadata.json

Remote: gs://my-bucket/resources/
  ├── sentiment_model/
  │   └── V2.1        (compressed)
  └── training_data/
      └── V3.0        (compressed)
```

### Use Cases

1. **ML Model Distribution**: Distribute trained models across team/deployments
2. **Dataset Management**: Version control for datasets
3. **Configuration Distribution**: Share configuration across environments
4. **Reproducibility**: Ensure consistent resource versions
5. **Offline Support**: Cache resources locally for offline use

### Best Practices

1. **Versioning**: Use semantic versioning (major.minor.patch)
2. **Immutability**: Never modify resources after upload
3. **Documentation**: Include README or metadata in resources
4. **Size Management**: Keep resources reasonably sized (<1GB recommended)
5. **Testing**: Test resource loading before uploading

---

## Reporting

**Module**: `dstools.reporting`

Structured reporting system for generating analysis reports, metrics, and logs.

### Core Components

**Reporter**: Singleton managing report generation
**ReportWriter**: Handles writing reports in various formats
**@report Decorator**: Marks functions as report generators

### API Reference

```python
def init_report(folder: Optional[Path] = None) -> None
    """Initialize the global reporter."""

@report(filename: Union[str, Path]) -> Callable
    """Decorator for report generation functions."""

class ReportWriter:
    def write_json(self, data: Dict[str, Any]) -> None
    def write_csv(self, data: list, headers: Optional[list] = None) -> None
    def write_plain_text(self, text: str) -> None
    def write_bytes(self, data: bytes) -> None
```

### Examples

**Basic Setup**:
```python
from dstools.reporting import init_report, report, ReportWriter

# Initialize (creates ~/.dono/reports/<script_name>/<timestamp>)
init_report()

# Or specify custom folder
init_report(folder=Path('/tmp/my_reports'))
```

**JSON Reports**:
```python
from dstools.reporting import report, ReportWriter

@report('model_metrics.json')
def report_model_metrics(writer: ReportWriter):
    metrics = {
        "accuracy": 0.945,
        "precision": 0.923,
        "recall": 0.956,
        "f1_score": 0.939,
        "training_time": "2h 15m",
        "dataset_size": 10000
    }
    writer.write_json(metrics)

# Generate report
report_model_metrics()
```

**CSV Reports**:
```python
@report('results.csv')
def report_experiment_results(writer: ReportWriter):
    headers = ['experiment', 'accuracy', 'loss', 'time']
    data = [
        ['baseline', 0.85, 0.32, 120],
        ['improved', 0.91, 0.21, 150],
        ['optimized', 0.93, 0.18, 135]
    ]
    writer.write_csv(data, headers=headers)

report_experiment_results()
```

**Text Reports**:
```python
@report('summary.txt')
def report_summary(writer: ReportWriter):
    summary = """
    Analysis Summary
    ================

    Dataset: Customer Reviews
    Total Records: 50,000
    Date Range: 2023-01-01 to 2023-12-31

    Key Findings:
    - 85% positive sentiment
    - Peak activity in Q4
    - Most common topic: Product Quality

    Recommendations:
    1. Focus on product quality messaging
    2. Increase support during Q4
    3. Monitor negative sentiment trends
    """
    writer.write_plain_text(summary.strip())

report_summary()
```

**Binary Reports** (e.g., plots):
```python
import matplotlib.pyplot as plt
import io

@report('accuracy_plot.png')
def report_accuracy_plot(writer: ReportWriter):
    epochs = range(1, 11)
    accuracy = [0.7, 0.75, 0.8, 0.82, 0.85, 0.87, 0.88, 0.89, 0.90, 0.91]

    plt.figure(figsize=(10, 6))
    plt.plot(epochs, accuracy, marker='o')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Model Accuracy over Epochs')
    plt.grid(True)

    # Save to bytes
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    writer.write_bytes(buffer.getvalue())
    plt.close()

report_accuracy_plot()
```

**Multiple Reports**:
```python
from dstools.reporting import init_report, report, ReportWriter

def run_analysis():
    init_report()

    # Generate multiple reports
    report_metrics()
    report_results()
    report_summary()
    report_plots()

    # All saved to same timestamped folder

@report('metrics.json')
def report_metrics(writer: ReportWriter):
    # ...

@report('results.csv')
def report_results(writer: ReportWriter):
    # ...

run_analysis()
```

**Conditional Reporting**:
```python
from dstools.reporting import Reporter, report, ReportWriter

# Only generate reports if enabled
if should_generate_reports:
    init_report()

@report('debug_info.json')
def report_debug_info(writer: ReportWriter):
    # Only runs if reporter is initialized
    writer.write_json({"debug": "information"})

# Safe to call even if not initialized
report_debug_info()  # No-op if reporter not initialized
```

### Report Organization

Default report structure:
```
~/.dono/reports/
└── my_analysis_script/
    └── 20240115_143022/
        ├── model_metrics.json
        ├── results.csv
        ├── summary.txt
        └── accuracy_plot.png
```

### Use Cases

1. **Experiment Tracking**: Record ML experiment results
2. **Analysis Reports**: Generate business analysis reports
3. **Model Evaluation**: Document model performance
4. **Data Quality**: Report data quality metrics
5. **Audit Trails**: Create audit logs of processing runs
6. **Automated Reporting**: Generate reports in scheduled jobs

### Best Practices

1. **Initialization**: Call `init_report()` at the start of your script
2. **Naming**: Use descriptive filenames with extensions
3. **Organization**: Group related reports in single run
4. **Timestamps**: Leverage automatic timestamping for tracking
5. **Formats**: Choose appropriate format (JSON for structured data, CSV for tables)

---

## Data Management

**Module**: `dstools.data_manage`

Integration with Google Cloud Firestore for data management with specialized collections.

### Core Components

**DataManager**: Main interface for data operations
**Collections**: Type-safe collection wrappers
**Schemas**: Data models for records

### DataManager

**Initialization**:
```python
from google.cloud import firestore
from dstools.data_manage.data_manager import DataManager
from dstools.storage.handlers.async_handler import AsyncStorageHandler

firestore_client = firestore.AsyncClient()
storage_handler = AsyncStorageHandler(config)
dm = DataManager(firestore_client, storage_handler)
```

**Methods**:
```python
# Iteration
async def iterate_collection(collection: str, fields: Optional[Sequence[str]]) -> AsyncStreamGenerator[dict]
async def iterate_record_ids(collection: str) -> AsyncStreamGenerator[str]

# Raw Pages
async def insert_raw_pages(raw_pages: Sequence[RawPageRecord]) -> int
async def fetch_raw_pages(page_ids: Sequence[str]) -> Iterable[RawPageRecord]
async def fetch_raw_pages_metadata(page_ids: Sequence[str]) -> Iterable[RawPageMetadataRecord]

# Enriched Pages
async def insert_enriched_pages(enriched_pages: Sequence[EnrichedPageRecord]) -> int
async def fetch_enriched_pages(page_ids: Sequence[str]) -> Iterable[EnrichedPageRecord]
```

### Examples

**Initialize DataManager**:
```python
import asyncio
from google.cloud import firestore
from dstools.data_manage.data_manager import DataManager
from dstools.storage.handlers.async_handler import AsyncStorageHandler
from dstools.storage.handlers.storage_handler import StorageHandlerFactory

async def setup():
    # Firestore client
    firestore_client = firestore.AsyncClient.from_service_account_json(
        'credentials.json'
    )

    # Storage handler
    storage_config = {
        'bucket': 'my-bucket',
        'credentials_path': 'credentials.json'
    }
    storage_handler = AsyncStorageHandler(
        StorageHandlerFactory.get_handler('GCS', storage_config)
    )

    # Data manager
    dm = DataManager(firestore_client, storage_handler)
    return dm

dm = asyncio.run(setup())
```

**Iterate Collections**:
```python
async def process_collection():
    dm = await setup()

    # Iterate all records
    async for record in dm.iterate_collection('users'):
        process_user(record)

    # Iterate specific fields
    async for record in dm.iterate_collection('users', fields=['email', 'name']):
        send_email(record['email'], record['name'])

    # Iterate IDs only
    async for user_id in dm.iterate_record_ids('users'):
        print(user_id)

asyncio.run(process_collection())
```

**Work with Raw Pages**:
```python
from dstools.data_manage.schema import RawPageRecord

async def process_raw_pages():
    dm = await setup()

    # Insert raw pages
    pages = [
        RawPageRecord(
            id='page1',
            content='<html>...</html>',
            url='https://example.com/page1',
            timestamp='2024-01-01T00:00:00Z'
        ),
        RawPageRecord(
            id='page2',
            content='<html>...</html>',
            url='https://example.com/page2',
            timestamp='2024-01-01T00:01:00Z'
        )
    ]

    inserted_count = await dm.insert_raw_pages(pages)
    print(f"Inserted {inserted_count} pages")

    # Fetch pages
    page_ids = ['page1', 'page2']
    fetched_pages = await dm.fetch_raw_pages(page_ids)

    for page in fetched_pages:
        print(f"Page: {page.id}, URL: {page.url}")

    # Fetch metadata only (no content)
    metadata = await dm.fetch_raw_pages_metadata(page_ids)
    for meta in metadata:
        print(f"Page: {meta.id}, URL: {meta.url}")

asyncio.run(process_raw_pages())
```

**Work with Enriched Pages**:
```python
from dstools.data_manage.schema import EnrichedPageRecord

async def process_enriched_pages():
    dm = await setup()

    # Insert enriched pages
    enriched = [
        EnrichedPageRecord(
            id='page1',
            extracted_text='This is the extracted text...',
            entities=['Entity1', 'Entity2'],
            sentiment=0.8
        )
    ]

    await dm.insert_enriched_pages(enriched)

    # Fetch enriched pages
    pages = await dm.fetch_enriched_pages(['page1'])
    for page in pages:
        print(f"Sentiment: {page.sentiment}")

asyncio.run(process_enriched_pages())
```

**Batch Processing**:
```python
from dstools.common.async_iter_utils import async_chunked

async def batch_process():
    dm = await setup()

    # Process in batches
    async for batch in async_chunked(
        dm.iterate_record_ids('raw_page'),
        chunk_size=100
    ):
        pages = await dm.fetch_raw_pages(batch)
        enriched = process_pages(pages)
        await dm.insert_enriched_pages(enriched)

asyncio.run(batch_process())
```

### Collections

**Firestore Collection**:
```python
from dstools.data_manage.firestore import FirestoreCollectionClient

collection = FirestoreCollectionClient('my_collection', firestore_client)

# Insert
await collection.insert(records)

# Fetch
records = await collection.fetch(record_ids)

# Update
await collection.update(record_id, data)

# Delete
await collection.delete(record_id)
```

**Generic Collection**:
```python
from dstools.data_manage.collections.firestore_collection import GeneralAsyncFirestoreCollection
from dstools.data_manage.schema import DataDBRecord

class MyRecord(DataDBRecord):
    # Define your record schema
    pass

collection = GeneralAsyncFirestoreCollection[MyRecord](
    'collection_name',
    MyRecord,
    firestore_client
)
```

### Use Cases

1. **Web Scraping**: Store and process scraped web pages
2. **Document Processing**: Manage document processing pipeline
3. **Data Enrichment**: Store raw and enriched data separately
4. **Content Management**: Manage content with metadata
5. **ETL Pipelines**: Extract, transform, and load data workflows

### Best Practices

1. **Batch Operations**: Use batch inserts/fetches for efficiency
2. **Field Selection**: Only fetch needed fields to reduce bandwidth
3. **Async Processing**: Leverage async for concurrent operations
4. **Error Handling**: Handle Firestore exceptions appropriately
5. **Indexing**: Create Firestore indexes for common queries
6. **Pagination**: Use chunking for large datasets

---

## Advanced Usage Patterns

### Combining Multiple Utilities

**ETL Pipeline**:
```python
import asyncio
from dstools.common.time_measure import DurationMeasure
from dstools.common.iter_utils import chunked
from dstools.common.json_io import write_json_lines
from dstools.reporting import init_report, report, ReportWriter
from dstools.storage.handlers.storage_handler import StorageHandlerFactory

def run_etl_pipeline():
    init_report()

    with DurationMeasure(action='ETL Pipeline'):
        # Extract
        data = extract_data()

        # Transform in batches
        transformed = []
        for batch in chunked(data, chunk_size=1000):
            transformed.extend(transform_batch(batch))

        # Load
        write_json_lines('output.jsonl', transformed)

        # Upload to cloud
        gcs = StorageHandlerFactory.get_handler('GCS', config)
        with open('output.jsonl', 'rb') as f:
            gcs.upload(f.read(), 'etl/output.jsonl')

        # Report
        generate_report(len(transformed))

@report('etl_stats.json')
def generate_report(writer: ReportWriter, record_count):
    writer.write_json({
        'records_processed': record_count,
        'status': 'success'
    })
```

**Resource-Based ML Pipeline**:
```python
from dstools.resource_management.resource import Resource
from dstools.common.time_measure import DurationMeasure
from dstools.reporting import init_report, report, ReportWriter
import pickle

class TrainingData(Resource, resource_name='training_data', version='1.0'):
    def __init__(self):
        super().__init__()
        self.train_file = self.local_path / 'train.csv'
        self.test_file = self.local_path / 'test.csv'

class Model(Resource, resource_name='model', version='2.0'):
    def __init__(self):
        super().__init__()
        self.model_file = self.local_path / 'model.pkl'

    def save_model(self, model):
        self.local_path.mkdir(parents=True, exist_ok=True)
        with open(self.model_file, 'wb') as f:
            pickle.dump(model, f)

def train_and_save():
    init_report()

    # Load training data (auto-downloads if needed)
    data_resource = TrainingData()

    # Train
    with DurationMeasure(action='model training') as dm:
        model = train_model(data_resource.train_file)

    # Save and upload
    model_resource = Model()
    model_resource.save_model(model)
    model_resource.upload()

    # Report
    report_training_results(dm.duration)
```

---

## Troubleshooting

### Common Issues

**Storage Handler Issues**:
```python
# Problem: GCS authentication fails
# Solution: Verify credentials path
config = {
    'bucket': 'my-bucket',
    'credentials_path': os.path.expanduser('~/.gcp/credentials.json')
}

# Problem: Permission denied
# Solution: Check service account has proper IAM roles
# Required roles: Storage Object Admin
```

**Resource Management Issues**:
```python
# Problem: Resource not found
# Solution: Ensure resource was uploaded and config is correct

# Check if resource exists in storage
gcs = StorageHandlerFactory.get_handler('GCS', config)
if gcs.exists('resources/my_resource/V1.0'):
    print("Resource exists")
else:
    print("Resource not found - upload it first")
```

**Compression Issues**:
```python
# Problem: Decompression fails
# Solution: Ensure same compression mode
compressor = FolderCompressor(SnappyCompressor(), mode='gz')
compressed = compressor.compress_folder(path)
# Must decompress with same mode
compressor.decompress_to_folder(compressed, output)
```

---

## Performance Tips

1. **Use Chunking**: Process large datasets in chunks to manage memory
2. **Leverage Async**: Use async I/O for concurrent operations
3. **Compression**: Compress data before storage/transfer
4. **Batch Operations**: Batch database operations when possible
5. **Lazy Evaluation**: Use iterators instead of lists for large datasets
6. **Caching**: Cache frequently accessed resources locally

---

## Contributing

When adding new utilities, follow these guidelines:

1. **Type Hints**: Use type hints for all function signatures
2. **Documentation**: Add docstrings with examples
3. **Testing**: Include unit tests
4. **Consistency**: Follow existing patterns and naming conventions
5. **Examples**: Add usage examples to this documentation
