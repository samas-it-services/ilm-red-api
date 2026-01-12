#!/usr/bin/env python3
"""Migrate files from Supabase Storage to Azure Blob Storage (INCREMENTAL).

Features:
- Skips already-uploaded files
- Retry logic for failed downloads
- Sequential processing to avoid rate limits
- Progress tracking

Usage:
    python scripts/migrate_files_incremental.py
    python scripts/migrate_files_incremental.py --dry-run
"""

import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass, field
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


@dataclass
class FileStats:
    books_downloaded: int = 0
    books_uploaded: int = 0
    books_skipped: int = 0
    thumbnails_downloaded: int = 0
    thumbnails_uploaded: int = 0
    thumbnails_skipped: int = 0
    errors: list = field(default_factory=list)
    file_updates: list = field(default_factory=list)


def get_uploaded_files(container_client) -> tuple[set, set]:
    """Get sets of already-uploaded book IDs."""
    book_files = set()
    covers = set()

    for blob in container_client.list_blobs():
        parts = blob.name.split('/')
        if len(parts) == 2:
            book_id = parts[0]
            if 'file.' in parts[1]:
                book_files.add(book_id)
            elif 'cover' in parts[1]:
                covers.add(book_id)

    return book_files, covers


def download_with_retry(supabase: Client, bucket: str, path: str, max_retries: int = 3) -> bytes | None:
    """Download a file with retry logic."""
    for attempt in range(max_retries):
        try:
            data = supabase.storage.from_(bucket).download(path)
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                # Wait before retry (exponential backoff)
                time.sleep(2 ** attempt)
            else:
                raise e
    return None


def download_and_upload_files(
    books: list[dict],
    dry_run: bool = False,
) -> FileStats:
    """Download files from Supabase and upload to Azure sequentially."""
    stats = FileStats()

    # Create Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    container_client = None
    uploaded_books = set()
    uploaded_covers = set()

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
            pass

        # Get already-uploaded files
        print("Checking for already-uploaded files...")
        uploaded_books, uploaded_covers = get_uploaded_files(container_client)
        print(f"Found {len(uploaded_books)} book files, {len(uploaded_covers)} covers already uploaded")

    print(f"\n=== Processing {len(books)} books ===")
    for book in tqdm(books, desc="Books"):
        book_id = book.get("id")
        file_path = book.get("file_path")
        file_type = book.get("file_type", "pdf")
        thumbnail_path = book.get("thumbnail_path")

        file_update = {"book_id": book_id, "file_path": None, "cover_url": None}

        # Download and upload book file
        if file_path:
            if book_id in uploaded_books:
                stats.books_skipped += 1
                azure_path = f"{book_id}/file.{file_type}"
                file_update["file_path"] = azure_path
            else:
                try:
                    # Download with retry
                    file_bytes = download_with_retry(supabase, "books", file_path)
                    if file_bytes:
                        stats.books_downloaded += 1

                        if not dry_run:
                            # Upload to Azure
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
                            file_update["file_path"] = azure_path

                except Exception as e:
                    error_msg = str(e)
                    if len(error_msg) > 80:
                        error_msg = error_msg[:80] + "..."
                    stats.errors.append(f"Book {book_id}: {error_msg}")

        # Download and upload thumbnail
        if thumbnail_path:
            if book_id in uploaded_covers:
                stats.thumbnails_skipped += 1
                file_update["cover_url"] = f"{book_id}/cover.jpg"
            else:
                try:
                    # Download with retry
                    thumb_bytes = download_with_retry(supabase, "book-thumbnails", thumbnail_path)
                    if thumb_bytes:
                        stats.thumbnails_downloaded += 1

                        if not dry_run:
                            # Upload to Azure
                            azure_thumb_path = f"{book_id}/cover.jpg"
                            blob_client = container_client.get_blob_client(azure_thumb_path)

                            content_settings = ContentSettings(content_type="image/jpeg")
                            blob_client.upload_blob(
                                thumb_bytes,
                                overwrite=True,
                                content_settings=content_settings
                            )
                            stats.thumbnails_uploaded += 1
                            file_update["cover_url"] = azure_thumb_path

                except Exception as e:
                    error_msg = str(e)
                    if len(error_msg) > 80:
                        error_msg = error_msg[:80] + "..."
                    stats.errors.append(f"Thumbnail {book_id}: {error_msg}")

        # Track updates for database
        if file_update["file_path"] or file_update["cover_url"]:
            stats.file_updates.append(file_update)

        # Small delay to avoid rate limiting
        time.sleep(0.1)

    return stats


async def update_database_paths(file_updates: list[dict]) -> None:
    """Update the target database with new Azure file paths."""
    if not file_updates:
        print("No database updates needed")
        return

    conn = await asyncpg.connect(TARGET_DB_URL)

    try:
        updated = 0
        print(f"\n=== Updating {len(file_updates)} book records in database ===")
        for update in tqdm(file_updates, desc="DB Updates"):
            book_id = update["book_id"]

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

        print(f"Updated {updated} book records")

    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Migrate files from Supabase to Azure (incremental)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download files but don't upload or update database"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("FILE MIGRATION: Supabase -> Azure (Incremental)")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN MODE ***\n")

    # Load books from exported JSON
    books_file = EXPORT_DIR / "books.json"
    if not books_file.exists():
        print(f"ERROR: {books_file} not found")
        return

    with open(books_file) as f:
        data = json.load(f)
        books = data.get("books", [])

    print(f"Found {len(books)} books to process")

    # Run the sequential file migration
    stats = download_and_upload_files(books, dry_run=args.dry_run)

    # Update database with new file paths
    if not args.dry_run:
        await update_database_paths(stats.file_updates)

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Books downloaded:      {stats.books_downloaded}")
    print(f"Books uploaded:        {stats.books_uploaded}")
    print(f"Books skipped:         {stats.books_skipped}")
    print(f"Thumbnails downloaded: {stats.thumbnails_downloaded}")
    print(f"Thumbnails uploaded:   {stats.thumbnails_uploaded}")
    print(f"Thumbnails skipped:    {stats.thumbnails_skipped}")
    print(f"Database updates:      {len(stats.file_updates)}")
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
