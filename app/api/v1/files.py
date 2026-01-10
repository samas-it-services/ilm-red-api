"""File serving endpoint for local storage (development only)."""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.storage import get_storage_provider
from app.storage.local import LocalStorageProvider

router = APIRouter()


@router.get("/{file_path:path}")
async def serve_file(
    file_path: str,
    expires: int = Query(..., description="Expiration timestamp"),
    signature: str = Query(..., description="HMAC signature"),
):
    """
    Serve files from local storage with signed URL validation.

    This endpoint only works with LocalStorageProvider (development).
    In production, Azure Blob Storage serves files directly via CDN.
    """
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
