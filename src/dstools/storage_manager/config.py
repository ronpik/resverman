"""
Configuration management for storage abstraction layer.

This module handles configuration loading from various sources:
1. Explicit configuration passed to constructor
2. Environment variables
3. Configuration files
4. Default values
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path

from .exceptions import InvalidConfigurationError, MissingCredentialsError


class StorageConfig:
    """Base configuration class for storage backends."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize storage configuration.

        Args:
            config: Configuration dictionary
            **kwargs: Additional configuration parameters
        """
        self._config = config or {}
        self._config.update(kwargs)
        self._validate()

    def _validate(self):
        """Validate configuration. Override in subclasses."""
        pass

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config.copy()

    @classmethod
    def from_env(cls, prefix: str = "DSTOOLS_") -> "StorageConfig":
        """
        Load configuration from environment variables.

        Args:
            prefix: Prefix for environment variables

        Returns:
            StorageConfig instance
        """
        config = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix) :].lower()
                # Try to parse as JSON for complex types
                try:
                    config[config_key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    config[config_key] = value

        return cls(config)

    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> "StorageConfig":
        """
        Load configuration from file (YAML or JSON).

        Args:
            file_path: Path to configuration file

        Returns:
            StorageConfig instance
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise InvalidConfigurationError(f"Configuration file not found: {file_path}")

        with open(file_path, "r") as f:
            if file_path.suffix in [".yaml", ".yml"]:
                try:
                    config = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    raise InvalidConfigurationError(f"Invalid YAML: {e}")
            elif file_path.suffix == ".json":
                try:
                    config = json.load(f)
                except json.JSONDecodeError as e:
                    raise InvalidConfigurationError(f"Invalid JSON: {e}")
            else:
                raise InvalidConfigurationError(
                    f"Unsupported file format: {file_path.suffix}"
                )

        # Interpolate environment variables
        config = cls._interpolate_env_vars(config)

        return cls(config)

    @classmethod
    def _interpolate_env_vars(cls, config: Any) -> Any:
        """
        Recursively interpolate environment variables in configuration.

        Supports ${VAR_NAME} syntax.

        Args:
            config: Configuration value (dict, list, str, etc.)

        Returns:
            Configuration with interpolated values
        """
        if isinstance(config, dict):
            return {k: cls._interpolate_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [cls._interpolate_env_vars(v) for v in config]
        elif isinstance(config, str):
            # Simple environment variable interpolation
            if config.startswith("${") and config.endswith("}"):
                var_name = config[2:-1]
                return os.environ.get(var_name, config)
            return config
        else:
            return config


class DBStorageConfig(StorageConfig):
    """Configuration for database storage."""

    def _validate(self):
        """Validate database storage configuration."""
        storage_type = self.get("storage_type")
        if not storage_type:
            raise InvalidConfigurationError("storage_type is required")

        # Validate based on storage type
        if storage_type == "postgresql":
            required = ["host", "database", "user", "password"]
            for field in required:
                if not self.get(field):
                    raise MissingCredentialsError(
                        f"PostgreSQL requires '{field}' in configuration"
                    )

        elif storage_type == "mongodb":
            if not self.get("connection_string") and not self.get("host"):
                raise MissingCredentialsError(
                    "MongoDB requires 'connection_string' or 'host' in configuration"
                )

        elif storage_type == "firestore":
            if not self.get("project_id"):
                raise MissingCredentialsError(
                    "Firestore requires 'project_id' in configuration"
                )
            if not self.get("credentials_path") and not self.get("credentials"):
                raise MissingCredentialsError(
                    "Firestore requires 'credentials_path' or 'credentials' in configuration"
                )

        elif storage_type == "sqlite":
            if not self.get("database_path"):
                raise InvalidConfigurationError(
                    "SQLite requires 'database_path' in configuration"
                )


class ObjectStoreConfig(StorageConfig):
    """Configuration for object storage."""

    def _validate(self):
        """Validate object store configuration."""
        storage_type = self.get("storage_type")
        if not storage_type:
            raise InvalidConfigurationError("storage_type is required")

        # Validate based on storage type
        if storage_type in ["s3", "minio", "do_spaces"]:
            required = ["bucket_name"]
            for field in required:
                if not self.get(field):
                    raise InvalidConfigurationError(
                        f"{storage_type} requires '{field}' in configuration"
                    )

            # Check for credentials (can come from environment or config)
            if not self.get("access_key_id") and not os.environ.get(
                "AWS_ACCESS_KEY_ID"
            ):
                raise MissingCredentialsError(
                    f"{storage_type} requires 'access_key_id' or AWS_ACCESS_KEY_ID environment variable"
                )

        elif storage_type in ["filesystem", "filesystem_temp", "filesystem_persistent"]:
            if not self.get("base_path") and storage_type != "filesystem_temp":
                raise InvalidConfigurationError(
                    f"{storage_type} requires 'base_path' in configuration"
                )


class StorageManagerConfig(StorageConfig):
    """Configuration for StorageManager."""

    def _validate(self):
        """Validate storage manager configuration."""
        if not self.get("db_storage") and not self.get("object_store"):
            raise InvalidConfigurationError(
                "StorageManager requires at least 'db_storage' or 'object_store' configuration"
            )

    def get_db_config(self) -> Optional[DBStorageConfig]:
        """Get database storage configuration."""
        db_config = self.get("db_storage")
        if db_config:
            return DBStorageConfig(db_config)
        return None

    def get_object_store_config(self) -> Optional[ObjectStoreConfig]:
        """Get object store configuration."""
        object_store_config = self.get("object_store")
        if object_store_config:
            return ObjectStoreConfig(object_store_config)
        return None


def load_config(
    config: Optional[Union[Dict[str, Any], str, Path]] = None,
    config_file: Optional[Union[str, Path]] = None,
    from_env: bool = True,
    env_prefix: str = "DSTOOLS_",
) -> StorageConfig:
    """
    Load configuration from various sources.

    Priority order:
    1. Explicit configuration passed as argument
    2. Configuration file
    3. Environment variables
    4. Default values

    Args:
        config: Explicit configuration dictionary or path to config file
        config_file: Path to configuration file
        from_env: Whether to load from environment variables
        env_prefix: Prefix for environment variables

    Returns:
        StorageConfig instance
    """
    result_config = {}

    # Load from environment variables (lowest priority)
    if from_env:
        env_config = StorageConfig.from_env(env_prefix)
        result_config.update(env_config.to_dict())

    # Load from config file (medium priority)
    if config_file:
        file_config = StorageConfig.from_file(config_file)
        result_config.update(file_config.to_dict())

    # Load from explicit config (highest priority)
    if config:
        if isinstance(config, (str, Path)):
            explicit_config = StorageConfig.from_file(config)
            result_config.update(explicit_config.to_dict())
        elif isinstance(config, dict):
            result_config.update(config)

    return StorageConfig(result_config)
