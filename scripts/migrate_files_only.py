#!/usr/bin/env python3
"""Migrate files from Supabase Storage to Azure Blob Storage.

This script:
1. Reads exported books.json for file paths
2. Downloads files from Supabase Storage (books, thumbnails)
3. Uploads to Azure Blob Storage
4. Updates Azure PostgreSQL with new file paths

Usage:
    python scripts/migrate_files_only.py
    python scripts/migrate_files_only.py --dry-run
"""

import argparse
import asyncio
import json
import os
from pathlib import Path

import asyncpg
from azure.storage.blob import BlobServiceClient, ContentSettings
from supabase import Client, create_client
from tqdm import tqdm

# Paths
SCRIPT_DIR = Path(__file__).parent
EXPORT_DIR = SCRIPT_DIR.parent / "exports" / "supabase_migration"

# Supabase Storage - Set these environment variables before running
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", f"https://{SUPABASE_PROJECT_ID}.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "books")

# Target PostgreSQL
TARGET_DB_URL = os.getenv("TARGET_DATABASE_URL", "")

# MIME types
MIME_TYPES = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
    "txt": "text/plain",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class FileStats:
    def __init__(self):
        self.books_downloaded = 0
        self.books_uploaded = 0
        self.thumbnails_downloaded = 0
        self.thumbnails_uploaded = 0
        self.errors = []


def create_supabase_client() -> Client:
    """Create a Supabase client for storage operations."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def download_and_upload_files(dry_run: bool = False) -> FileStats:
    """Download files from Supabase and upload to Azure."""
    stats = FileStats()

    # Load books from exported JSON
    books_file = EXPORT_DIR / "books.json"
    if not books_file.exists():
        print(f"ERROR: {books_file} not found. Run full migration first.")
        return stats

    with open(books_file) as f:
        data = json.load(f)
        books = data.get("books", [])

    print(f"Found {len(books)} books to process")

    # Create directories
    files_dir = EXPORT_DIR / "files"
    thumbnails_dir = EXPORT_DIR / "thumbnails"
    files_dir.mkdir(parents=True, exist_ok=True)
    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    # Create clients
    supabase = create_supabase_client()

    if not dry_run:
        blob_service = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service.get_container_client(AZURE_STORAGE_CONTAINER)

        # Ensure container exists
        try:
            container_client.create_container()
            print(f"Created container: {AZURE_STORAGE_CONTAINER}")
        except Exception:
            pass  # Container already exists

    # Track file path updates for database
    file_updates = []

    print("\n=== Downloading and uploading book files ===")
    for book in tqdm(books, desc="Books"):
        book_id = book.get("id")
        file_path = book.get("file_path")
        file_type = book.get("file_type", "pdf")
        thumbnail_path = book.get("thumbnail_path")

        # Download and upload book file
        if file_path:
            try:
                # Download from Supabase
                file_bytes = supabase.storage.from_("books").download(file_path)
                stats.books_downloaded += 1

                if not dry_run and file_bytes:
                    # Upload to Azure: books/{bookId}/file.{ext}
                    azure_path = f"{book_id}/file.{file_type}"
                    blob_client = container_client.get_blob_client(azure_path)

                    content_settings = ContentSettings(
                        content_type=MIME_TYPES.get(file_type, "application/octet-stream")
                    )
                    blob_client.upload_blob(
                        file_bytes,
                        overwrite=True,
                        content_settings=content_settings
                    )
                    stats.books_uploaded += 1

                    file_updates.append({
                        "book_id": book_id,
                        "file_path": azure_path,
                        "cover_url": None  # Set separately
                    })

            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                stats.errors.append(f"Book {book_id}: {error_msg}")

        # Download and upload thumbnail
        if thumbnail_path:
            try:
                # Download from Supabase
                thumb_bytes = supabase.storage.from_("book-thumbnails").download(thumbnail_path)
                stats.thumbnails_downloaded += 1

                if not dry_run and thumb_bytes:
                    # Upload to Azure: books/{bookId}/cover.jpg
                    azure_thumb_path = f"{book_id}/cover.jpg"
                    blob_client = container_client.get_blob_client(azure_thumb_path)

                    content_settings = ContentSettings(content_type="image/jpeg")
                    blob_client.upload_blob(
                        thumb_bytes,
                        overwrite=True,
                        content_settings=content_settings
                    )
                    stats.thumbnails_uploaded += 1

                    # Update file_updates with cover URL
                    for update in file_updates:
                        if update["book_id"] == book_id:
                            update["cover_url"] = azure_thumb_path
                            break
                    else:
                        file_updates.append({
                            "book_id": book_id,
                            "file_path": None,
                            "cover_url": azure_thumb_path
                        })

            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 100:
                    error_msg = error_msg[:100] + "..."
                stats.errors.append(f"Thumbnail {book_id}: {error_msg}")

    # Update database with new file paths
    if not dry_run and file_updates:
        print("\n=== Updating database with new file paths ===")
        await update_database_paths(file_updates)

    return stats


async def update_database_paths(file_updates: list[dict]) -> None:
    """Update the target database with new Azure file paths."""
    conn = await asyncpg.connect(TARGET_DB_URL)

    try:
        updated = 0
        for update in tqdm(file_updates, desc="DB Updates"):
            book_id = update["book_id"]

            # Build update query dynamically
            set_clauses = []
            values = [book_id]
            param_idx = 2

            if update.get("file_path"):
                set_clauses.append(f"file_path = ${param_idx}")
                values.append(update["file_path"])
                param_idx += 1

            if update.get("cover_url"):
                set_clauses.append(f"cover_url = ${param_idx}")
                values.append(update["cover_url"])
                param_idx += 1

            if set_clauses:
                query = f"UPDATE books SET {', '.join(set_clauses)} WHERE id = $1"
                await conn.execute(query, *values)
                updated += 1

        print(f"Updated {updated} book records in database")

    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate files from Supabase to Azure Blob Storage"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download files but don't upload or update database"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("FILE MIGRATION: Supabase Storage → Azure Blob Storage")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be uploaded\n")

    stats = await download_and_upload_files(dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Books downloaded:      {stats.books_downloaded}")
    print(f"Books uploaded:        {stats.books_uploaded}")
    print(f"Thumbnails downloaded: {stats.thumbnails_downloaded}")
    print(f"Thumbnails uploaded:   {stats.thumbnails_uploaded}")
    print(f"Errors:                {len(stats.errors)}")

    if stats.errors:
        print("\nErrors (first 20):")
        for error in stats.errors[:20]:
            print(f"  - {error}")
        if len(stats.errors) > 20:
            print(f"  ... and {len(stats.errors) - 20} more")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
