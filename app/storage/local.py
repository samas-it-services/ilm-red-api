"""Local file system storage provider."""

import hashlib
import hmac
import os
import time
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlencode

import aiofiles
import aiofiles.os

from app.config import settings
from app.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Local file system storage provider.

    Stores files in the local filesystem. For development and testing.
    In production, consider using Azure Blob Storage or S3.
    """

    def __init__(self, base_path: str | None = None, secret_key: str | None = None):
        """Initialize local storage provider.

        Args:
            base_path: Base directory for file storage
            secret_key: Secret key for signing URLs (uses JWT secret if not provided)
        """
        self.base_path = Path(base_path or settings.local_storage_path)
        self.secret_key = secret_key or settings.jwt_secret

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path for a storage path."""
        # Sanitize path to prevent directory traversal
        safe_path = Path(path).as_posix().lstrip("/")
        return self.base_path / safe_path

    async def upload(
        self,
        path: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file to local storage."""
        full_path = self._get_full_path(path)

        # Create parent directories if needed
        await aiofiles.os.makedirs(full_path.parent, exist_ok=True)

        # Write file
        if isinstance(data, bytes):
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
        else:
            # File-like object
            async with aiofiles.open(full_path, "wb") as f:
                while chunk := data.read(8192):
                    await f.write(chunk)

        return path

    async def download(self, path: str) -> bytes:
        """Download file from local storage."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def get_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
        for_download: bool = True,
    ) -> str:
        """Generate a signed URL for temporary access.

        For local storage, we create a URL with a signature that can be
        verified by the API server. This is useful for development/testing.
        """
        # Calculate expiration timestamp
        expires_at = int(time.time()) + expires_in

        # Create signature
        message = f"{path}:{expires_at}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()[:32]

        # Build query parameters
        params = {
            "expires": expires_at,
            "signature": signature,
        }

        # Return signed URL (relative path for local development)
        return f"/v1/files/{path}?{urlencode(params)}"

    def verify_signature(self, path: str, expires: int, signature: str) -> bool:
        """Verify a signed URL signature.

        Args:
            path: Storage path
            expires: Expiration timestamp
            signature: URL signature

        Returns:
            True if signature is valid and not expired
        """
        # Check expiration
        if time.time() > expires:
            return False

        # Verify signature
        message = f"{path}:{expires}"
        expected = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()[:32]

        return hmac.compare_digest(signature, expected)

    async def delete(self, path: str) -> None:
        """Delete file from local storage."""
        full_path = self._get_full_path(path)

        if full_path.exists():
            await aiofiles.os.remove(full_path)

            # Remove empty parent directories
            parent = full_path.parent
            while parent != self.base_path:
                try:
                    parent.rmdir()  # Only removes empty directories
                    parent = parent.parent
                except OSError:
                    break

    async def exists(self, path: str) -> bool:
        """Check if file exists in local storage."""
        full_path = self._get_full_path(path)
        return full_path.exists()

    async def get_size(self, path: str) -> int:
        """Get file size in bytes."""
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = await aiofiles.os.stat(full_path)
        return stat.st_size

    async def stream_file(self, path: str, chunk_size: int = 8192):
        """Stream file content in chunks.

        Useful for large files to avoid loading entire file into memory.
        """
        full_path = self._get_full_path(path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk
