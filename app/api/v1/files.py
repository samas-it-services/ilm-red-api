"""File serving endpoint for local storage (development only)."""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.storage import get_storage_provider
from app.storage.local import LocalStorageProvider

router = APIRouter()


@router.get(
    "/{file_path:path}",
    summary="Serve file (development only)",
    description="""
Serve files from local storage with signed URL validation.

**Development Only** - In production, files are served directly from Azure Blob Storage CDN with SAS tokens for better performance and global distribution.

**How It Works:**
1. Page generation creates files in local storage
2. URLs are generated with HMAC signatures and expiration
3. This endpoint validates the signature before serving
4. Files are cached for 1 hour

**URL Format:**
```
/v1/files/books/{book_id}/pages/thumb/1.jpg?expires=1704067200&signature=abc123...
```

**Parameters:**
- `expires` - Unix timestamp when URL expires (typically 6 hours from generation)
- `signature` - HMAC-SHA256 signature for validation

**Supported File Types:**
- `.jpg`, `.jpeg` - Page images (thumbnail, medium)
- `.png` - Cover images
- `.pdf` - Original book files
    """,
    responses={
        200: {"description": "File content returned successfully"},
        400: {"description": "Not available in production mode"},
        401: {"description": "Invalid or expired signature"},
        404: {"description": "File not found"},
    },
)
async def serve_file(
    file_path: str,
    expires: int = Query(..., description="Unix timestamp when URL expires"),
    signature: str = Query(..., description="HMAC-SHA256 signature for validation"),
):
    """Serve files from local storage with signed URL validation."""
    storage = get_storage_provider()

    # Only works for local storage
    if not isinstance(storage, LocalStorageProvider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct file serving only available in development mode",
        )

    # Validate signature
    if not storage.verify_signature(file_path, expires, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired signature",
        )

    # Get full file path
    full_path = storage.base_path / file_path
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Determine content type
    content_type = "application/octet-stream"
    if file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif file_path.endswith(".png"):
        content_type = "image/png"
    elif file_path.endswith(".pdf"):
        content_type = "application/pdf"

    return FileResponse(
        path=full_path,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )
