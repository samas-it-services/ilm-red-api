#!/usr/bin/env python3
"""Migrate data from Supabase (ilm-red-unbound) to PostgreSQL (ilm-red-api).

This script migrates:
- Users (profiles -> users)
- Books (books -> books) with files
- Ratings (book_ratings -> ratings)
- Favorites (book_favorites -> favorites)
- Chat sessions (book_chat_sessions -> chat_sessions)
- Chat messages (book_chat_messages -> chat_messages)

Usage:
    # Export only (to JSON files)
    python scripts/migrate_from_supabase.py --export-only

    # Full migration to production
    python scripts/migrate_from_supabase.py --target-url "postgresql+asyncpg://..."

    # Dry run (no writes)
    python scripts/migrate_from_supabase.py --dry-run

Environment variables:
    SUPABASE_URL: Supabase project URL
    SUPABASE_KEY: Supabase anon/service key (for storage)
    TARGET_DATABASE_URL: Target PostgreSQL URL
"""

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import httpx
from argon2 import PasswordHasher
from azure.storage.blob import BlobServiceClient, ContentSettings
from supabase import create_client, Client
from tqdm import tqdm

# Paths
SCRIPT_DIR = Path(__file__).parent
EXPORT_DIR = SCRIPT_DIR.parent / "exports" / "supabase_migration"

# Source (Supabase) - Set these environment variables before running
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", f"https://{SUPABASE_PROJECT_ID}.supabase.co")
# Use service role key for full storage access (private buckets)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Target (Azure PostgreSQL)
TARGET_DB_URL = os.getenv("TARGET_DATABASE_URL", "")

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "books")

# Category mapping (source -> target)
CATEGORY_MAP = {
    "quran": "quran",
    "hadith": "hadith",
    "fiqh": "fiqh",
    "seerah": "seerah",
    "aqidah": "aqidah",
    "tafsir": "tafsir",
    "history": "history",
    "islamic_history": "history",
    "spirituality": "spirituality",
    "children": "children",
    "fiction": "fiction",
    "non-fiction": "non-fiction",
    "education": "education",
    "science": "science",
    "technology": "technology",
    "biography": "biography",
    "self-help": "self-help",
    "other": "other",
}

# Password hasher
ph = PasswordHasher()


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.users_exported = 0
        self.users_imported = 0
        self.books_exported = 0
        self.books_imported = 0
        self.files_downloaded = 0
        self.files_uploaded = 0
        self.ratings_exported = 0
        self.ratings_imported = 0
        self.favorites_exported = 0
        self.favorites_imported = 0
        self.sessions_exported = 0
        self.sessions_imported = 0
        self.messages_exported = 0
        self.messages_imported = 0
        self.errors = []

    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Users:     {self.users_exported} exported, {self.users_imported} imported")
        print(f"Books:     {self.books_exported} exported, {self.books_imported} imported")
        print(f"Files:     {self.files_downloaded} downloaded, {self.files_uploaded} uploaded")
        print(f"Ratings:   {self.ratings_exported} exported, {self.ratings_imported} imported")
        print(f"Favorites: {self.favorites_exported} exported, {self.favorites_imported} imported")
        print(f"Sessions:  {self.sessions_exported} exported, {self.sessions_imported} imported")
        print(f"Messages:  {self.messages_exported} exported, {self.messages_imported} imported")
        print(f"Errors:    {len(self.errors)}")
        if self.errors:
            print("\nErrors:")
            for err in self.errors[:10]:
                print(f"  - {err}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
        print("=" * 60)


async def connect_source() -> asyncpg.Connection:
    """Connect to Supabase PostgreSQL."""
    print("Connecting to Supabase PostgreSQL...")
    # Disable statement cache for pgbouncer compatibility
    conn = await asyncpg.connect(SUPABASE_DB_URL, ssl="require", statement_cache_size=0)
    print("  Connected!")
    return conn


async def connect_target(target_url: str) -> asyncpg.Connection:
    """Connect to target PostgreSQL."""
    print(f"Connecting to target PostgreSQL...")
    # Convert SQLAlchemy URL to asyncpg format
    url = target_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    print("  Connected!")
    return conn


async def export_users(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export users from Supabase profiles table."""
    print("\nExporting users...")

    # Query profiles with auth.users join
    query = """
        SELECT
            p.id,
            p.email,
            p.username,
            p.full_name,
            p.profile_picture_url,
            p.bio,
            p.is_premium_user,
            p.created_at,
            p.updated_at
        FROM profiles p
        WHERE p.email IS NOT NULL
    """

    rows = await source.fetch(query)
    users = []

    for row in tqdm(rows, desc="  Users"):
        # Generate random password (users will use forgot password)
        random_password = secrets.token_urlsafe(32)
        password_hash = ph.hash(random_password)

        # Generate username from email if missing
        username = row["username"]
        if not username:
            # Use part before @ in email as username
            email_prefix = row["email"].split("@")[0]
            # Add random suffix to ensure uniqueness
            username = f"{email_prefix}_{secrets.token_hex(3)}"

        user = {
            "id": str(row["id"]),
            "email": row["email"],
            "username": username,
            "display_name": row["full_name"],
            "avatar_url": row["profile_picture_url"],
            "bio": row["bio"],
            "password_hash": password_hash,
            "roles": ["premium"] if row["is_premium_user"] else ["user"],
            "status": "active",
            "preferences": {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        users.append(user)
        stats.users_exported += 1

    print(f"  Exported {len(users)} users")
    return users


async def export_books(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export books from Supabase."""
    print("\nExporting books...")

    query = """
        SELECT
            id, user_id, title, author, description,
            category, language, visibility, is_public,
            file_path, file_name, file_size, mime_type,
            sha256_hash, thumbnail_path,
            view_count, uploaded_at, updated_at
        FROM books
        WHERE file_path IS NOT NULL
    """

    rows = await source.fetch(query)
    books = []

    for row in tqdm(rows, desc="  Books"):
        # Map category
        src_category = (row["category"] or "other").lower()
        category = CATEGORY_MAP.get(src_category, "other")

        # Determine visibility (map friends_only -> friends)
        visibility = "private"
        if row["visibility"]:
            src_vis = row["visibility"]
            # Map source visibility to target visibility
            visibility_map = {
                "public": "public",
                "private": "private",
                "friends": "friends",
                "friends_only": "friends",  # Map friends_only to friends
            }
            visibility = visibility_map.get(src_vis, "private")
        elif row["is_public"]:
            visibility = "public"

        # Extract file type from mime_type
        mime_type = row["mime_type"] or "application/pdf"
        if "epub" in mime_type:
            file_type = "epub"
        elif "text" in mime_type:
            file_type = "txt"
        else:
            file_type = "pdf"

        book = {
            "id": str(row["id"]),
            "owner_id": str(row["user_id"]) if row["user_id"] else None,
            "title": row["title"] or "Untitled",
            "author": row["author"],
            "description": row["description"],
            "category": category,
            "language": row["language"] or "en",
            "visibility": visibility,
            "file_path": row["file_path"],
            "file_name": row["file_name"],
            "file_size": row["file_size"],
            "file_type": file_type,
            "file_hash": row["sha256_hash"],
            "thumbnail_path": row["thumbnail_path"],
            "view_count": row["view_count"] or 0,
            "created_at": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        books.append(book)
        stats.books_exported += 1

    print(f"  Exported {len(books)} books")
    return books


async def export_ratings(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export book ratings."""
    print("\nExporting ratings...")

    query = """
        SELECT id, user_id, book_id, rating, review, created_at, updated_at
        FROM book_ratings
    """

    rows = await source.fetch(query)
    ratings = []

    for row in tqdm(rows, desc="  Ratings"):
        rating = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "book_id": str(row["book_id"]),
            "rating": row["rating"],
            "review": row["review"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        ratings.append(rating)
        stats.ratings_exported += 1

    print(f"  Exported {len(ratings)} ratings")
    return ratings


async def export_favorites(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export book favorites."""
    print("\nExporting favorites...")

    query = """
        SELECT id, user_id, book_id, created_at
        FROM book_favorites
    """

    rows = await source.fetch(query)
    favorites = []

    for row in tqdm(rows, desc="  Favorites"):
        favorite = {
            "user_id": str(row["user_id"]),
            "book_id": str(row["book_id"]),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        favorites.append(favorite)
        stats.favorites_exported += 1

    print(f"  Exported {len(favorites)} favorites")
    return favorites


async def export_chat_sessions(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export chat sessions."""
    print("\nExporting chat sessions...")

    query = """
        SELECT
            id, user_id, book_id, session_name,
            message_count, created_at, updated_at
        FROM book_chat_sessions
        WHERE user_id IS NOT NULL
    """

    rows = await source.fetch(query)
    sessions = []

    for row in tqdm(rows, desc="  Sessions"):
        session = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "book_id": str(row["book_id"]) if row["book_id"] else None,
            "title": row["session_name"],
            "message_count": row["message_count"] or 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        sessions.append(session)
        stats.sessions_exported += 1

    print(f"  Exported {len(sessions)} sessions")
    return sessions


async def export_chat_messages(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export chat messages.

    Note: Chat messages in Supabase are encrypted (message_encrypted, response_encrypted).
    This function attempts to export them, but if the table is empty or encrypted,
    it will return an empty list.
    """
    print("\nExporting chat messages...")

    # Check if messages exist and are accessible
    try:
        count_query = "SELECT COUNT(*) FROM book_chat_messages"
        count = await source.fetchval(count_query)
        if count == 0:
            print("  No chat messages found (table empty or encrypted)")
            return []
    except Exception as e:
        print(f"  Cannot access chat messages: {e}")
        return []

    # Messages are encrypted in Supabase - we cannot decrypt them
    # Return empty list - chat history will not be migrated
    print("  Chat messages are encrypted - skipping migration")
    print("  (Users will start fresh with no chat history)")
    return []


def create_supabase_client() -> Client:
    """Create a Supabase client for storage operations."""
    # Use service role key for full storage access (private buckets)
    service_key = os.getenv("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY)
    return create_client(SUPABASE_URL, service_key)


async def download_files(
    books: list[dict],
    stats: MigrationStats,
    http_client: httpx.AsyncClient,
) -> None:
    """Download book files from Supabase Storage."""
    print("\nDownloading files from Supabase Storage...")

    files_dir = EXPORT_DIR / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    # Create Supabase client for storage
    supabase = create_supabase_client()

    for book in tqdm(books, desc="  Files"):
        file_path = book.get("file_path")
        if not file_path:
            continue

        try:
            # Download using Supabase storage client
            file_bytes = supabase.storage.from_("books").download(file_path)
            if file_bytes:
                # Save file locally
                local_path = files_dir / f"{book['id']}.{book['file_type']}"
                local_path.write_bytes(file_bytes)
                book["local_file_path"] = str(local_path)
                stats.files_downloaded += 1
        except Exception as e:
            error_msg = str(e)
            # Try to get signed URL as fallback
            try:
                signed_result = supabase.storage.from_("books").create_signed_url(
                    file_path, 3600  # 1 hour expiry
                )
                if signed_result and signed_result.get("signedURL"):
                    resp = await http_client.get(
                        signed_result["signedURL"], timeout=120.0
                    )
                    if resp.status_code == 200:
                        local_path = files_dir / f"{book['id']}.{book['file_type']}"
                        local_path.write_bytes(resp.content)
                        book["local_file_path"] = str(local_path)
                        stats.files_downloaded += 1
                        continue
            except Exception:
                pass
            stats.errors.append(f"Failed to download {file_path}: {error_msg}")

    print(f"  Downloaded {stats.files_downloaded} files")


async def download_thumbnails(
    books: list[dict],
    stats: MigrationStats,
    http_client: httpx.AsyncClient,
) -> None:
    """Download thumbnails from Supabase Storage."""
    print("\nDownloading thumbnails...")

    thumbs_dir = EXPORT_DIR / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    # Create Supabase client for storage
    supabase = create_supabase_client()

    downloaded = 0
    for book in tqdm(books, desc="  Thumbnails"):
        thumb_path = book.get("thumbnail_path")
        if not thumb_path:
            continue

        try:
            # Download using Supabase storage client
            file_bytes = supabase.storage.from_("thumbnails").download(thumb_path)
            if file_bytes:
                local_path = thumbs_dir / f"{book['id']}.jpg"
                local_path.write_bytes(file_bytes)
                book["local_thumbnail_path"] = str(local_path)
                downloaded += 1
        except Exception:
            # Try public URL as fallback (thumbnails bucket might be public)
            try:
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/thumbnails/{thumb_path}"
                resp = await http_client.get(public_url, timeout=60.0)
                if resp.status_code == 200:
                    local_path = thumbs_dir / f"{book['id']}.jpg"
                    local_path.write_bytes(resp.content)
                    book["local_thumbnail_path"] = str(local_path)
                    downloaded += 1
            except Exception:
                pass  # Thumbnails are optional

    print(f"  Downloaded {downloaded} thumbnails")


async def upload_to_azure(
    books: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Upload book files and thumbnails to Azure Blob Storage."""
    print("\nUploading files to Azure Blob Storage...")

    if dry_run:
        print("  Skipping upload (dry run)")
        return

    # Initialize Azure Blob client
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            AZURE_STORAGE_CONNECTION_STRING
        )
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER)

        # Create container if it doesn't exist
        try:
            container_client.create_container()
            print(f"  Created container: {AZURE_STORAGE_CONTAINER}")
        except Exception:
            pass  # Container already exists
    except Exception as e:
        print(f"  Failed to connect to Azure Blob Storage: {e}")
        stats.errors.append(f"Azure Blob connection failed: {e}")
        return

    uploaded = 0
    for book in tqdm(books, desc="  Uploading"):
        book_id = book["id"]

        # Upload main file
        local_file_path = book.get("local_file_path")
        if local_file_path and Path(local_file_path).exists():
            file_type = book.get("file_type", "pdf")
            blob_path = f"books/{book_id}/file.{file_type}"

            # Determine content type
            content_types = {
                "pdf": "application/pdf",
                "epub": "application/epub+zip",
                "txt": "text/plain",
            }
            content_type = content_types.get(file_type, "application/octet-stream")

            try:
                blob_client = container_client.get_blob_client(blob_path)
                with open(local_file_path, "rb") as f:
                    blob_client.upload_blob(
                        f,
                        overwrite=True,
                        content_settings=ContentSettings(content_type=content_type),
                    )
                stats.files_uploaded += 1
                uploaded += 1
            except Exception as e:
                stats.errors.append(f"Upload failed for {book['title']}: {e}")

        # Upload thumbnail
        local_thumb_path = book.get("local_thumbnail_path")
        if local_thumb_path and Path(local_thumb_path).exists():
            thumb_blob_path = f"books/{book_id}/cover.jpg"

            try:
                blob_client = container_client.get_blob_client(thumb_blob_path)
                with open(local_thumb_path, "rb") as f:
                    blob_client.upload_blob(
                        f,
                        overwrite=True,
                        content_settings=ContentSettings(content_type="image/jpeg"),
                    )
            except Exception as e:
                # Thumbnails are optional, don't add to errors
                pass

    print(f"  Uploaded {uploaded} files to Azure Blob Storage")


async def import_users(
    target: asyncpg.Connection,
    users: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> tuple[set[str], dict[str, str]]:
    """Import users to target database.

    Returns:
        tuple: (valid_user_ids, user_id_map)
            - valid_user_ids: Set of user IDs that exist in target DB
            - user_id_map: Dict mapping source user ID -> target user ID
    """
    print("\nImporting users...")

    # First, get all existing users from target (id + email)
    valid_user_ids = set()
    email_to_id: dict[str, str] = {}
    user_id_map: dict[str, str] = {}  # source_id -> target_id

    if not dry_run:
        existing = await target.fetch("SELECT id, email FROM users")
        for row in existing:
            user_id = str(row["id"])
            valid_user_ids.add(user_id)
            email_to_id[row["email"]] = user_id

    for user in tqdm(users, desc="  Users"):
        source_id = user["id"]
        email = user["email"]

        if dry_run:
            valid_user_ids.add(source_id)
            user_id_map[source_id] = source_id
            stats.users_imported += 1
            continue

        # Check if email already exists in target
        if email in email_to_id:
            # User exists with this email - map source ID to existing target ID
            target_id = email_to_id[email]
            user_id_map[source_id] = target_id
            stats.users_imported += 1
            continue

        try:
            # Insert new user with source ID
            await target.execute(
                """
                INSERT INTO users (
                    id, email, username, display_name, avatar_url, bio,
                    password_hash, roles, status, preferences,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    avatar_url = EXCLUDED.avatar_url,
                    bio = EXCLUDED.bio,
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(source_id),
                email,
                user["username"],
                user.get("display_name"),
                user.get("avatar_url"),
                user.get("bio"),
                user["password_hash"],
                user["roles"],
                user["status"],
                json.dumps(user.get("preferences", {})),
                datetime.fromisoformat(user["created_at"]) if user["created_at"] else datetime.now(UTC),
                datetime.fromisoformat(user["updated_at"]) if user["updated_at"] else datetime.now(UTC),
            )
            valid_user_ids.add(source_id)
            user_id_map[source_id] = source_id
            email_to_id[email] = source_id
            stats.users_imported += 1
        except Exception as e:
            stats.errors.append(f"User {email}: {e}")

    print(f"  Imported {stats.users_imported} users")
    return valid_user_ids, user_id_map


async def import_books(
    target: asyncpg.Connection,
    books: list[dict],
    valid_user_ids: set[str],
    user_id_map: dict[str, str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import books to target database."""
    print("\nImporting books...")

    valid_book_ids = set()

    for book in tqdm(books, desc="  Books"):
        # Map source owner_id to target owner_id
        source_owner_id = book.get("owner_id")
        owner_id = None
        if source_owner_id:
            # First check if we have a mapping from import
            if source_owner_id in user_id_map:
                owner_id = user_id_map[source_owner_id]
            # Otherwise check if it's directly in valid_user_ids
            elif source_owner_id in valid_user_ids:
                owner_id = source_owner_id
            # If neither, owner doesn't exist - leave as NULL (orphan book)

        if dry_run:
            valid_book_ids.add(book["id"])
            stats.books_imported += 1
            continue

        try:
            # Generate file hash if missing
            file_hash = book.get("file_hash") or hashlib.sha256(book["id"].encode()).hexdigest()

            await target.execute(
                """
                INSERT INTO books (
                    id, owner_id, title, author, description,
                    category, language, visibility,
                    file_path, file_size, file_type, file_hash,
                    status, cover_url, stats,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                ON CONFLICT (id) DO UPDATE SET
                    owner_id = EXCLUDED.owner_id,
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(book["id"]),
                UUID(owner_id) if owner_id else None,
                book["title"],
                book.get("author"),
                book.get("description"),
                book["category"],
                book.get("language", "en"),
                book.get("visibility", "private"),
                f"books/{book['id']}/file.{book['file_type']}",  # New path
                book.get("file_size", 0),
                book.get("file_type", "pdf"),
                file_hash,
                "ready",  # Assume ready since we're migrating
                book.get("thumbnail_path"),
                json.dumps({"views": book.get("view_count", 0)}),
                datetime.fromisoformat(book["created_at"]) if book["created_at"] else datetime.now(UTC),
                datetime.fromisoformat(book["updated_at"]) if book["updated_at"] else datetime.now(UTC),
            )
            valid_book_ids.add(book["id"])
            stats.books_imported += 1
        except Exception as e:
            stats.errors.append(f"Book {book['title']}: {e}")

    print(f"  Imported {stats.books_imported} books")
    return valid_book_ids


async def import_ratings(
    target: asyncpg.Connection,
    ratings: list[dict],
    valid_user_ids: set[str],
    user_id_map: dict[str, str],
    valid_book_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import ratings to target database."""
    print("\nImporting ratings...")

    for rating in tqdm(ratings, desc="  Ratings"):
        # Map source user_id to target user_id
        source_user_id = rating["user_id"]
        target_user_id = user_id_map.get(source_user_id)
        if not target_user_id and source_user_id not in valid_user_ids:
            continue
        target_user_id = target_user_id or source_user_id

        if rating["book_id"] not in valid_book_ids:
            continue

        if dry_run:
            stats.ratings_imported += 1
            continue

        try:
            await target.execute(
                """
                INSERT INTO ratings (user_id, book_id, rating, review, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, book_id) DO NOTHING
                """,
                UUID(target_user_id),
                UUID(rating["book_id"]),
                rating["rating"],
                rating.get("review"),
                datetime.fromisoformat(rating["created_at"]) if rating["created_at"] else datetime.now(UTC),
                datetime.fromisoformat(rating["updated_at"]) if rating["updated_at"] else datetime.now(UTC),
            )
            stats.ratings_imported += 1
        except Exception as e:
            stats.errors.append(f"Rating: {e}")

    print(f"  Imported {stats.ratings_imported} ratings")


async def import_favorites(
    target: asyncpg.Connection,
    favorites: list[dict],
    valid_user_ids: set[str],
    user_id_map: dict[str, str],
    valid_book_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import favorites to target database."""
    print("\nImporting favorites...")

    for fav in tqdm(favorites, desc="  Favorites"):
        # Map source user_id to target user_id
        source_user_id = fav["user_id"]
        target_user_id = user_id_map.get(source_user_id)
        if not target_user_id and source_user_id not in valid_user_ids:
            continue
        target_user_id = target_user_id or source_user_id

        if fav["book_id"] not in valid_book_ids:
            continue

        if dry_run:
            stats.favorites_imported += 1
            continue

        try:
            await target.execute(
                """
                INSERT INTO favorites (user_id, book_id, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, book_id) DO NOTHING
                """,
                UUID(target_user_id),
                UUID(fav["book_id"]),
                datetime.fromisoformat(fav["created_at"]) if fav["created_at"] else datetime.now(UTC),
            )
            stats.favorites_imported += 1
        except Exception as e:
            stats.errors.append(f"Favorite: {e}")

    print(f"  Imported {stats.favorites_imported} favorites")


async def import_chat_sessions(
    target: asyncpg.Connection,
    sessions: list[dict],
    valid_user_ids: set[str],
    user_id_map: dict[str, str],
    valid_book_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import chat sessions to target database."""
    print("\nImporting chat sessions...")

    valid_session_ids = set()

    for session in tqdm(sessions, desc="  Sessions"):
        # Map source user_id to target user_id
        source_user_id = session["user_id"]
        target_user_id = user_id_map.get(source_user_id)
        if not target_user_id and source_user_id not in valid_user_ids:
            continue
        target_user_id = target_user_id or source_user_id

        # Book is optional, but if specified must exist
        book_id = session.get("book_id")
        if book_id and book_id not in valid_book_ids:
            book_id = None  # Clear invalid book reference

        if dry_run:
            valid_session_ids.add(session["id"])
            stats.sessions_imported += 1
            continue

        try:
            await target.execute(
                """
                INSERT INTO chat_sessions (
                    id, user_id, book_id, title, message_count,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(session["id"]),
                UUID(target_user_id),
                UUID(book_id) if book_id else None,
                session.get("title"),
                session.get("message_count", 0),
                datetime.fromisoformat(session["created_at"]) if session["created_at"] else datetime.now(UTC),
                datetime.fromisoformat(session["updated_at"]) if session["updated_at"] else datetime.now(UTC),
            )
            valid_session_ids.add(session["id"])
            stats.sessions_imported += 1
        except Exception as e:
            stats.errors.append(f"Session: {e}")

    print(f"  Imported {stats.sessions_imported} sessions")
    return valid_session_ids


async def import_chat_messages(
    target: asyncpg.Connection,
    messages: list[dict],
    valid_session_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import chat messages to target database."""
    print("\nImporting chat messages...")

    for msg in tqdm(messages, desc="  Messages"):
        if msg["session_id"] not in valid_session_ids:
            continue

        if dry_run:
            stats.messages_imported += 1
            continue

        try:
            await target.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(msg["id"]),
                UUID(msg["session_id"]),
                msg["role"],
                msg["content"],
                datetime.fromisoformat(msg["created_at"]) if msg["created_at"] else datetime.now(UTC),
            )
            stats.messages_imported += 1
        except Exception as e:
            stats.errors.append(f"Message: {e}")

    print(f"  Imported {stats.messages_imported} messages")


def save_export(data: dict, name: str) -> None:
    """Save exported data to JSON file."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EXPORT_DIR / f"{name}.json"
    output_file.write_text(json.dumps(data, indent=2, default=str))
    print(f"  Saved to {output_file}")


async def main(
    export_only: bool = False,
    dry_run: bool = False,
    target_url: str | None = None,
    skip_files: bool = False,
) -> int:
    """Main migration function."""
    print("\n" + "=" * 60)
    print("SUPABASE TO ILM-RED-API MIGRATION")
    print("=" * 60)
    print(f"Source: Supabase ({SUPABASE_PROJECT_ID})")
    print(f"Target: {'DRY RUN' if dry_run else (target_url or TARGET_DB_URL).split('@')[1].split('/')[0]}")
    print(f"Mode:   {'Export Only' if export_only else 'Full Migration'}")
    print("=" * 60)

    stats = MigrationStats()

    # Connect to source
    source = await connect_source()

    try:
        # Export data
        users = await export_users(source, stats)
        books = await export_books(source, stats)
        ratings = await export_ratings(source, stats)
        favorites = await export_favorites(source, stats)
        sessions = await export_chat_sessions(source, stats)
        messages = await export_chat_messages(source, stats)

        # Download files from Supabase and upload to Azure
        if not skip_files:
            async with httpx.AsyncClient() as http_client:
                await download_files(books, stats, http_client)
                await download_thumbnails(books, stats, http_client)
            # Upload to Azure Blob Storage
            await upload_to_azure(books, stats, dry_run)

        # Save exports
        print("\nSaving exports...")
        save_export({"users": users}, "users")
        save_export({"books": books}, "books")
        save_export({"ratings": ratings}, "ratings")
        save_export({"favorites": favorites}, "favorites")
        save_export({"sessions": sessions}, "sessions")
        save_export({"messages": messages}, "messages")

        if export_only:
            stats.print_summary()
            return 0

        # Connect to target
        target = await connect_target(target_url or TARGET_DB_URL)

        try:
            # Import data
            valid_user_ids, user_id_map = await import_users(target, users, stats, dry_run)
            valid_book_ids = await import_books(target, books, valid_user_ids, user_id_map, stats, dry_run)
            await import_ratings(target, ratings, valid_user_ids, user_id_map, valid_book_ids, stats, dry_run)
            await import_favorites(target, favorites, valid_user_ids, user_id_map, valid_book_ids, stats, dry_run)
            valid_session_ids = await import_chat_sessions(target, sessions, valid_user_ids, user_id_map, valid_book_ids, stats, dry_run)
            await import_chat_messages(target, messages, valid_session_ids, stats, dry_run)

        finally:
            await target.close()

    finally:
        await source.close()

    stats.print_summary()
    return 0 if len(stats.errors) == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate data from Supabase to ILM-RED-API"
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export data, don't import to target",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate import without writing to target",
    )
    parser.add_argument(
        "--target-url",
        help="Target database URL (overrides TARGET_DATABASE_URL)",
    )
    parser.add_argument(
        "--skip-files",
        action="store_true",
        help="Skip downloading files (for testing)",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(
        export_only=args.export_only,
        dry_run=args.dry_run,
        target_url=args.target_url,
        skip_files=args.skip_files,
    ))
    sys.exit(exit_code)
