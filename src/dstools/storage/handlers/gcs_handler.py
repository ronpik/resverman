import os
from pathlib import Path
from typing import Iterable, Iterator, Optional

from google.cloud import storage
from google.cloud.storage import Blob, Bucket
from globalog import LOG


from dstools.storage.handlers.storage_handler import StorageHandler


def get_src_root() -> Path:
    return Path(__file__).parent


class GCSHandler(StorageHandler):
    """Handler for storing files in Google Cloud Storage"""

    def __init__(self, storage_config: dict[str, str]):
        """
        Initialize the GCS handler.

        Args:
            storage_config: Dictionary containing at least the "bucket" key
        """
        self._bucket_name = storage_config["bucket"]

        # Try multiple credential sources
        self._client = None
        self._bucket = None

        # First try service account path from config
        credentials_path = storage_config.get("credentials_path")
        if credentials_path and os.path.exists(credentials_path):
            self._initialize_client(credentials_path)

        # Then try environment variable
        if not self._client and "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            env_creds_path = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            if os.path.exists(env_creds_path):
                self._initialize_client(env_creds_path)

        # If still no client, try Application Default Credentials
        if not self._client:
            try:
                LOG.info("Trying Application Default Credentials")
                self._client = storage.Client()
                self._bucket = self._client.bucket(self._bucket_name)
            except Exception as e:
                LOG.error(f"Failed to initialize using Application Default Credentials: {str(e)}")
                raise ValueError("Unable to authenticate with GCS")

        if not self._bucket:
            raise ValueError(f"Failed to get GCS bucket: {self._bucket_name}")

        LOG.info(f"Initialized GCS storage with bucket: {self._bucket_name}")

    def _initialize_client(self, credentials_path: str) -> bool:
        """Initialize the GCS client using the given credentials file"""
        try:
            LOG.info(f"Initializing GCS client with credentials from: {credentials_path}")
            self._client = storage.Client.from_service_account_json(credentials_path)
            self._bucket = self._client.bucket(self._bucket_name)
            return True
        except Exception as e:
            LOG.warning(f"Failed to initialize GCS client with credentials from {credentials_path}: {str(e)}")
            return False

    def get_client(self) -> storage.Client:
        return self._client

    def get_bucket(self) -> Optional[Bucket]:
        return self._bucket


    def download(self, remote_relative_path: str) -> bytes:
        blob = self._bucket.blob(remote_relative_path)
        LOG.debug(f"Downloading from GCS: {remote_relative_path}")
        content = blob.download_as_bytes()
        LOG.debug(f"Downloaded {len(content)} bytes from GCS at {remote_relative_path}.")
        return content

    def upload(self, content: bytes, remote_relative_path: str) -> bool:
        try:
            blob = self._bucket.blob(remote_relative_path)
            LOG.debug(f"Uploading {len(content)} bytes to GCS at {remote_relative_path}")
            blob.upload_from_string(content)
            LOG.debug(f"Uploaded to GCS: {remote_relative_path}")
            return True
        except Exception as e:
            LOG.error(f"Failed to upload to GCS at {remote_relative_path}", exc_info=e)
            return False

    def exists(self, remote_relative_path: str) -> bool:
        """Check if file exists in GCS"""
        blob = self._bucket.blob(remote_relative_path)
        return blob.exists()

    def size(self, remote_relative_path: str) -> int:
        blob = self._bucket.get_blob(remote_relative_path)
        return blob.size if blob else 0

    def list_objects(self, prefix: str) -> Iterator[Blob]:
        """List objects in GCS with the given prefix"""
        yield from self._bucket.list_blobs(prefix=prefix)
