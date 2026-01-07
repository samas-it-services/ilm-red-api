"""Storage providers package."""

from functools import lru_cache

from app.config import settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    """Get the configured storage provider.

    Returns the appropriate storage provider based on configuration.
    Uses lru_cache to return the same instance.
    """
    if settings.storage_type == "azure":
        from app.storage.azure_blob import AzureBlobStorageProvider

        return AzureBlobStorageProvider()
    elif settings.storage_type == "s3":
        # S3 provider would be implemented here
        raise NotImplementedError("S3 storage provider not yet implemented")
    else:
        return LocalStorageProvider()


__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "get_storage_provider",
]
