"""
Filesystem-based object storage implementations.

This module provides object storage backed by the local filesystem,
suitable for development, testing, and simple deployments.
"""

import os
import shutil
import json
import hashlib
import tempfile
import atexit
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path
from datetime import datetime

from .base import BaseObjectStore, ObjectMetadata
from ..exceptions import (
    ObjectNotFoundError,
    ValidationError,
    OperationError,
    ObjectStoreConnectionError,
)


class FilesystemObjectStore(BaseObjectStore):
    """
    Filesystem-based object storage.

    Features:
    - Store objects as files in directory structure
    - Preserve directory hierarchy
    - Metadata stored in sidecar files or in-memory
    - Support for relative and absolute paths
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize filesystem object store.

        Args:
            config: Configuration dictionary with:
                - base_path: Base directory for storage
                - create_base_path: Create directory if doesn't exist (default: True)
                - metadata_storage: "sidecar" or "memory" (default: "sidecar")
                - file_permissions: File permissions octal string (default: "0644")
        """
        super().__init__(config)

        self._base_path_str = config.get("base_path")
        if not self._base_path_str:
            raise ValidationError("base_path is required for filesystem storage")

        self._base_path_obj = Path(self._base_path_str)
        self._create_base_path = config.get("create_base_path", True)
        self._metadata_storage = config.get("metadata_storage", "sidecar")
        self._file_permissions = int(config.get("file_permissions", "0644"), 8)

        # In-memory metadata cache
        self._metadata_cache: Dict[str, ObjectMetadata] = {}
        self._connected = False

    def connect(self) -> None:
        """Establish connection (ensure base path exists)."""
        if self._create_base_path:
            self._base_path_obj.mkdir(parents=True, exist_ok=True)
        elif not self._base_path_obj.exists():
            raise ObjectStoreConnectionError(
                f"Base path does not exist: {self._base_path_obj}"
            )

        self._connected = True

    def disconnect(self) -> None:
        """Close connection and clear cache."""
        self._metadata_cache.clear()
        self._connected = False

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def _get_file_path(self, key: str) -> Path:
        """Get full file path for object key."""
        full_key = self.get_full_key(key)
        return self._base_path_obj / full_key

    def _get_metadata_path(self, key: str) -> Path:
        """Get path to metadata sidecar file."""
        return self._get_file_path(key).with_suffix(".meta.json")

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate MD5 checksum of data."""
        return hashlib.md5(data).hexdigest()

    def put(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ObjectMetadata:
        """Store an object."""
        self.validate_key(key)

        file_path = self._get_file_path(key)

        try:
            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write object data
            with open(file_path, "wb") as f:
                f.write(data)

            # Set file permissions
            os.chmod(file_path, self._file_permissions)

            # Create metadata
            obj_metadata = ObjectMetadata(
                key=key,
                size_bytes=len(data),
                content_type=content_type or self.detect_content_type(key),
                last_modified=datetime.now(),
                checksum=f"md5:{self._calculate_checksum(data)}",
                custom_metadata=metadata,
            )

            # Store metadata
            self._store_metadata(key, obj_metadata)

            return obj_metadata

        except Exception as e:
            raise OperationError(f"Failed to put object '{key}': {e}")

    def get(self, key: str) -> bytes:
        """Retrieve object content."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            raise ObjectNotFoundError(key)

        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise OperationError(f"Failed to get object '{key}': {e}")

    def delete(self, key: str) -> bool:
        """Delete an object."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return False

        try:
            # Delete object file
            file_path.unlink()

            # Delete metadata
            if self._metadata_storage == "sidecar":
                metadata_path = self._get_metadata_path(key)
                if metadata_path.exists():
                    metadata_path.unlink()
            else:
                self._metadata_cache.pop(key, None)

            # Remove empty parent directories
            try:
                file_path.parent.rmdir()
            except OSError:
                # Directory not empty, that's fine
                pass

            return True

        except Exception as e:
            raise OperationError(f"Failed to delete object '{key}': {e}")

    def exists(self, key: str) -> bool:
        """Check if an object exists."""
        return self._get_file_path(key).exists()

    def get_metadata(self, key: str) -> ObjectMetadata:
        """Get object metadata."""
        if not self.exists(key):
            raise ObjectNotFoundError(key)

        # Try to load metadata
        if self._metadata_storage == "sidecar":
            metadata_path = self._get_metadata_path(key)
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        metadata_dict = json.load(f)
                        return ObjectMetadata(
                            key=metadata_dict["key"],
                            size_bytes=metadata_dict["size_bytes"],
                            content_type=metadata_dict["content_type"],
                            last_modified=datetime.fromisoformat(
                                metadata_dict["last_modified"]
                            ),
                            checksum=metadata_dict.get("checksum"),
                            custom_metadata=metadata_dict.get("custom_metadata"),
                        )
                except Exception:
                    pass

        # Fallback: generate metadata from file stats
        file_path = self._get_file_path(key)
        stat = file_path.stat()

        return ObjectMetadata(
            key=key,
            size_bytes=stat.st_size,
            content_type=self.detect_content_type(key),
            last_modified=datetime.fromtimestamp(stat.st_mtime),
            checksum=None,
            custom_metadata=None,
        )

    def list_objects(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[str]:
        """List object keys."""
        keys = []

        # Determine search path
        if prefix:
            search_path = self._base_path_obj / self.get_full_key(prefix)
            if not search_path.exists():
                return []
        else:
            search_path = self._base_path_obj

        # Walk directory tree
        for root, dirs, files in os.walk(search_path):
            for file in files:
                # Skip metadata files
                if file.endswith(".meta.json"):
                    continue

                file_path = Path(root) / file

                # Get relative key
                try:
                    rel_path = file_path.relative_to(self._base_path_obj)
                    key = str(rel_path)

                    # Filter by prefix if specified
                    if prefix and not key.startswith(prefix):
                        continue

                    keys.append(key)
                except ValueError:
                    # Path not relative to base path, skip
                    continue

        # Sort keys
        keys.sort()

        # Apply offset and limit
        if offset:
            keys = keys[offset:]
        if limit:
            keys = keys[:limit]

        return keys

    def list_objects_with_metadata(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ObjectMetadata]:
        """List objects with metadata."""
        keys = self.list_objects(prefix=prefix, limit=limit, offset=offset)

        metadata_list = []
        for key in keys:
            try:
                metadata = self.get_metadata(key)
                metadata_list.append(metadata)
            except ObjectNotFoundError:
                # Object was deleted between listing and metadata fetch
                pass

        return metadata_list

    def _store_metadata(self, key: str, metadata: ObjectMetadata) -> None:
        """Store metadata for an object."""
        if self._metadata_storage == "sidecar":
            metadata_path = self._get_metadata_path(key)
            try:
                with open(metadata_path, "w") as f:
                    json.dump(metadata.to_dict(), f, indent=2)
                os.chmod(metadata_path, self._file_permissions)
            except Exception:
                # Metadata storage is best-effort
                pass
        else:
            self._metadata_cache[key] = metadata


class TemporaryFilesystemObjectStore(FilesystemObjectStore):
    """
    Temporary filesystem object storage.

    Features:
    - Uses system temp directory
    - Automatic cleanup on process exit
    - Suitable for testing and temporary data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize temporary filesystem object store.

        Args:
            config: Configuration dictionary with optional:
                - temp_dir: Custom temp directory (default: system temp)
                - cleanup_on_exit: Cleanup on exit (default: True)
        """
        # Create temporary directory
        temp_dir = config.get("temp_dir")
        if temp_dir:
            self._temp_dir_obj = Path(temp_dir)
            self._temp_dir_obj.mkdir(parents=True, exist_ok=True)
            self._temp_dir = str(self._temp_dir_obj)
            self._created_temp = False
        else:
            self._temp_dir = tempfile.mkdtemp(prefix="dstools_storage_")
            self._temp_dir_obj = Path(self._temp_dir)
            self._created_temp = True

        # Update config with temp directory
        config = config.copy()
        config["base_path"] = self._temp_dir
        config["create_base_path"] = True

        super().__init__(config)

        self._cleanup_on_exit = config.get("cleanup_on_exit", True)

        # Register cleanup
        if self._cleanup_on_exit:
            atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        """Cleanup temporary directory."""
        if self._temp_dir_obj.exists() and self._created_temp:
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                # Best-effort cleanup
                pass

    def disconnect(self) -> None:
        """Close connection and cleanup if configured."""
        super().disconnect()
        if self._cleanup_on_exit:
            self._cleanup()


class PersistentFilesystemObjectStore(FilesystemObjectStore):
    """
    Persistent filesystem object storage.

    Features:
    - Retain objects between runs
    - Optional automatic backups
    - Configurable retention policies
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize persistent filesystem object store.

        Args:
            config: Configuration dictionary with:
                - base_path: Base directory for storage
                - enable_backups: Enable backups (default: False)
                - backup_path: Backup directory
        """
        super().__init__(config)

        self._enable_backups = config.get("enable_backups", False)
        self._backup_path = config.get("backup_path")

        if self._enable_backups and self._backup_path:
            self._backup_path_obj = Path(self._backup_path)
            self._backup_path_obj.mkdir(parents=True, exist_ok=True)

    def put(
        self,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ObjectMetadata:
        """Store an object with optional backup."""
        # Store object normally
        obj_metadata = super().put(key, data, content_type, metadata)

        # Create backup if enabled
        if self._enable_backups and self._backup_path:
            try:
                backup_file = self._backup_path_obj / f"{key}.backup"
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                with open(backup_file, "wb") as f:
                    f.write(data)
            except Exception:
                # Backup is best-effort
                pass

        return obj_metadata
