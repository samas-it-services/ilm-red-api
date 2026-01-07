"""Base storage provider abstraction."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProvider(ABC):
    """Abstract base class for storage providers.

    This abstraction allows switching between local file storage,
    Azure Blob Storage, AWS S3, or any other storage backend.
    """

    @abstractmethod
    async def upload(
        self,
        path: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to storage.

        Args:
            path: Storage path (e.g., "books/{uuid}/file.pdf")
            data: File content as bytes or file-like object
            content_type: MIME type of the file

        Returns:
            The storage path where the file was stored
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download file from storage.

        Args:
            path: Storage path

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    async def get_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
        for_download: bool = True,
    ) -> str:
        """Generate a signed URL for temporary access.

        Args:
            path: Storage path
            expires_in: URL expiration time in seconds (default: 1 hour)
            for_download: If True, include Content-Disposition header

        Returns:
            Signed URL for temporary access
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete file from storage.

        Args:
            path: Storage path
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists in storage.

        Args:
            path: Storage path

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_size(self, path: str) -> int:
        """Get file size in bytes.

        Args:
            path: Storage path

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass
