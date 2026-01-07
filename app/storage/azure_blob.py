"""Azure Blob Storage provider."""

from datetime import datetime, timezone, timedelta
from typing import BinaryIO

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)

from app.config import settings
from app.storage.base import StorageProvider


class AzureBlobStorageProvider(StorageProvider):
    """Azure Blob Storage provider.

    Production-ready storage provider using Azure Blob Storage.
    Supports SAS token generation for secure, time-limited access.
    """

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str | None = None,
    ):
        """Initialize Azure Blob Storage provider.

        Args:
            connection_string: Azure Storage connection string
            container_name: Blob container name
        """
        self.connection_string = connection_string or settings.azure_storage_connection_string
        self.container_name = container_name or settings.azure_storage_container

        if not self.connection_string:
            raise ValueError("Azure Storage connection string is required")

        # Initialize the blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )

        # Get container client
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )

        # Create container if it doesn't exist
        try:
            self.container_client.create_container()
        except Exception:
            # Container already exists
            pass

    async def upload(
        self,
        path: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to Azure Blob Storage."""
        blob_client = self.container_client.get_blob_client(path)

        # Set content settings
        content_settings = ContentSettings(content_type=content_type)

        # Upload the blob
        if isinstance(data, bytes):
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=content_settings,
            )
        else:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=content_settings,
            )

        return path

    async def download(self, path: str) -> bytes:
        """Download file from Azure Blob Storage."""
        blob_client = self.container_client.get_blob_client(path)

        try:
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except Exception as e:
            if "BlobNotFound" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise

    async def get_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
        for_download: bool = True,
    ) -> str:
        """Generate a SAS URL for temporary access."""
        blob_client = self.container_client.get_blob_client(path)

        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            container_name=self.container_name,
            blob_name=path,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            content_disposition="attachment" if for_download else None,
        )

        # Build full URL
        return f"{blob_client.url}?{sas_token}"

    async def delete(self, path: str) -> None:
        """Delete file from Azure Blob Storage."""
        blob_client = self.container_client.get_blob_client(path)

        try:
            blob_client.delete_blob()
        except Exception as e:
            if "BlobNotFound" not in str(e):
                raise

    async def exists(self, path: str) -> bool:
        """Check if file exists in Azure Blob Storage."""
        blob_client = self.container_client.get_blob_client(path)

        try:
            blob_client.get_blob_properties()
            return True
        except Exception:
            return False

    async def get_size(self, path: str) -> int:
        """Get file size in bytes."""
        blob_client = self.container_client.get_blob_client(path)

        try:
            properties = blob_client.get_blob_properties()
            return properties.size
        except Exception as e:
            if "BlobNotFound" in str(e):
                raise FileNotFoundError(f"File not found: {path}")
            raise

    async def list_blobs(self, prefix: str = "") -> list[str]:
        """List all blobs with a given prefix.

        Args:
            prefix: Filter blobs by prefix (e.g., "books/{book_id}/")

        Returns:
            List of blob paths
        """
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
