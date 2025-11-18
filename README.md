# dstools

A comprehensive collection of utility tools for data science and Python projects, providing simplified interfaces for storage, resource management, reporting, compression, and common operations.

## Installation

Install the package from your local repository:

```bash
pip install .
```

Or install from GitHub:

```bash
pip install git+https://github.com/username/dstools.git
```

## Quick Start

### Time Measurement

Easily measure execution time with automatic unit adjustment:

```python
from dstools.common.time_measure import DurationMeasure, TimeUnit

# Measure with milliseconds
with DurationMeasure(action='processing data', unit=TimeUnit.MILLISECONDS):
    # Your code here
    process_large_dataset()

# Access measured duration
with DurationMeasure(action='api call', unit=TimeUnit.SECONDS, fallback=True) as dm:
    response = make_api_call()
print(f"Duration: {dm.duration:.2f}{dm._get_unit_suffix(dm.used_unit)}")
```

### JSON I/O

Simple JSON and JSONL file operations:

```python
from dstools.common.json_io import write_json, read_json, write_json_lines, read_json_lines

# Write and read JSON
data = {"name": "example", "value": 42}
write_json(data, "config.json")
loaded = read_json("config.json")

# Write and read JSONL (JSON Lines)
records = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
write_json_lines("data.jsonl", records)
for record in read_json_lines("data.jsonl"):
    print(record)
```

### Storage Handlers

Unified interface for different storage backends:

```python
from dstools.storage.handlers.storage_handler import StorageHandlerFactory

# Local storage
local_config = {'root_dir': '/path/to/data'}
local_storage = StorageHandlerFactory.get_handler('LOCAL', local_config)
local_storage.upload(b'data', 'file.txt')
content = local_storage.download('file.txt')

# Google Cloud Storage
gcs_config = {
    'bucket': 'my-bucket',
    'credentials_path': 'path/to/credentials.json'
}
gcs_storage = StorageHandlerFactory.get_handler('GCS', gcs_config)
gcs_storage.upload(b'data', 'remote/path/file.txt')
```

### Compression

Compress and decompress data or folders:

```python
from dstools.compression.snappy_compressor import SnappyCompressor
from dstools.compression.folder_compress import FolderCompressor
from pathlib import Path

# Compress bytes
compressor = SnappyCompressor()
compressed = compressor.compress(b"large data content")
decompressed = compressor.decompress(compressed)

# Compress entire folders
folder_compressor = FolderCompressor(compressor, mode='gz')
compressed_folder = folder_compressor.compress_folder(Path('/path/to/folder'))
folder_compressor.decompress_to_folder(compressed_folder, Path('/output/path'))
```

### Resource Management

Version-controlled resource management with automatic download/upload:

```python
from dstools.resource_management.resource import Resource

# Define a versioned resource
class MyDataset(Resource, resource_name='dataset', version='1.0'):
    def __init__(self):
        super().__init__()
        self.data_file = self.local_path / 'data.csv'

    def get_data(self):
        # Resource is automatically downloaded if not present locally
        with open(self.data_file) as f:
            return f.read()

# Use the resource
dataset = MyDataset()  # Singleton pattern
data = dataset.get_data()

# Upload a new version
dataset.upload()
```

### Reporting

Structured reporting and logging system:

```python
from dstools.reporting import init_report, report, ReportWriter

# Initialize reporting
init_report()  # Creates ~/.dono/reports/<script_name>/<timestamp>

# Use decorator for report generation
@report('analysis_results.json')
def generate_analysis(writer: ReportWriter):
    results = {"accuracy": 0.95, "loss": 0.12}
    writer.write_json(results)

@report('metrics.csv')
def generate_metrics(writer: ReportWriter):
    data = [['epoch', 'loss'], [1, 0.5], [2, 0.3]]
    writer.write_csv(data[1:], headers=data[0])

generate_analysis()
generate_metrics()
```

### Iterator Utilities

Powerful iterator manipulation functions:

```python
from dstools.common.iter_utils import chunked, merge_iters, make_unique, partition

# Chunk an iterable
for chunk in chunked(range(100), chunk_size=10):
    process_batch(chunk)  # Process 10 items at a time

# Merge sorted iterables
iter1 = [1, 4, 7]
iter2 = [2, 5, 8]
merged = merge_iters(iter1, iter2, key=lambda x: x)  # [1, 2, 4, 5, 7, 8]

# Remove duplicates while preserving order
unique_items = list(make_unique([1, 2, 2, 3, 1, 4]))  # [1, 2, 3, 4]

# Partition by predicate
evens, odds = partition(lambda x: x % 2 == 0, [1, 2, 3, 4, 5, 6])
```

### Async I/O

Asynchronous file operations:

```python
from dstools.common.aio_utils import write_text, read_text, write_bytes, read_bytes
import asyncio

async def process_files():
    # Async write and read
    await write_text('async_file.txt', 'Hello Async World')
    content = await read_text('async_file.txt')

    # Async binary operations
    await write_bytes('data.bin', b'\x00\x01\x02')
    data = await read_bytes('data.bin')

asyncio.run(process_files())
```

### Image Utilities

Image I/O and conversion utilities:

```python
from dstools.common.image_utils import image_from_bytes, image_to_bytes, store_image
from pathlib import Path

# Load image from bytes
image = image_from_bytes(image_bytes)

# Convert image to bytes
png_bytes = image_to_bytes(image, format='png')

# Save image to disk
store_image(image, Path('output.jpg'), format='jpg')
```

## Features

- **Common Utilities**: Time measurement, JSON I/O, iterator tools, async I/O
- **Storage**: Unified interface for Local, GCS, S3, and SSH storage
- **Compression**: Snappy compression for bytes and folders
- **Resource Management**: Version-controlled resource system with automatic sync
- **Reporting**: Structured logging and report generation
- **Image Processing**: PIL-based image utilities
- **Data Management**: Firestore integration and collection management
- **Async Support**: Full async/await support for I/O operations

## Configuration

### Resource Management Configuration

Create a configuration file at `~/.dstools/rvs.json` or in your project:

```json
{
  "resources_root": "~/.dstools/resources",
  "remote_root": "resources",
  "storage": {
    "remote_storage_type": "GCS",
    "storage_config": {
      "bucket": "my-bucket",
      "credentials_path": "/path/to/credentials.json"
    }
  }
}
```

## Documentation

For detailed documentation on each utility, including use cases and advanced examples, see [DOCS.md](DOCS.md).

## Requirements

- Python >= 3.8
- Dependencies: globalog, google-cloud-storage, google-cloud-firestore, aiofiles, Pillow, opencv-python, python-snappy

## License

MIT License
