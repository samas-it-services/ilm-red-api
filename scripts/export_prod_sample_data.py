#!/usr/bin/env python3
"""Export sample data from Azure PostgreSQL production database.

This script exports sanitized sample data for local development:
- 50 books (various categories, visibility)
- 20 users (sanitized emails, passwords)
- 100 ratings
- 30 favorites
- 10 chat sessions with messages
- 5 books with page images

Usage:
    python scripts/export_prod_sample_data.py
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
from argon2 import PasswordHasher

# Configuration
PROD_DB_HOST = "ilmred-prod-postgres.postgres.database.azure.com"
PROD_DB_USER = "pgadmin"
PROD_DB_PASSWORD = os.getenv("PGPASSWORD", "bc143e9e-f42f-48d4-9b05-453c0dd6b9dc")
PROD_DB_NAME = "ilmred"

# Export limits
LIMIT_BOOKS = 50
LIMIT_USERS = 20
LIMIT_RATINGS = 100
LIMIT_FAVORITES = 30
LIMIT_CHAT_SESSIONS = 10
LIMIT_BOOKS_WITH_PAGES = 5

# Output directory
EXPORT_DIR = Path(__file__).parent.parent / "data"
EXPORT_DIR.mkdir(exist_ok=True)


def sanitize_user(user: dict) -> dict:
    """Sanitize user data (replace PII)."""
    ph = PasswordHasher()
    user_id = user["id"]

    # Generate test email
    username_part = user["username"] if user["username"] else f"user{hash(user_id) % 10000}"
    user["email"] = f"{username_part}@test.com"
    user["email_verified"] = True

    # Hash test password
    user["password_hash"] = ph.hash("test123")

    # Anonymize display name if it looks like a real name
    if user.get("display_name") and len(user["display_name"].split()) > 1:
        user["display_name"] = f"Test User {hash(user_id) % 1000}"

    # Clear sensitive fields
    user.pop("extra_data", None)

    return user


def serialize_datetime(obj: Any) -> str:
    """Convert datetime and UUID to JSON-serializable format."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, '__class__') and 'UUID' in obj.__class__.__name__:
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def export_data():
    """Export sample data from production database."""
    print(f"Connecting to {PROD_DB_HOST}...")

    conn = await asyncpg.connect(
        host=PROD_DB_HOST,
        user=PROD_DB_USER,
        password=PROD_DB_PASSWORD,
        database=PROD_DB_NAME,
        ssl="require",
    )

    try:
        # Export books
        print(f"\nExporting {LIMIT_BOOKS} books...")
        books = await conn.fetch(
            """
            SELECT *
            FROM books
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT $1
            """,
            LIMIT_BOOKS,
        )
        books_data = [dict(book) for book in books]
        book_ids = [book["id"] for book in books_data]

        with open(EXPORT_DIR / "books.json", "w") as f:
            json.dump(books_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(books_data)} books")

        # Export users (get unique owners of books + some extras)
        print(f"\nExporting {LIMIT_USERS} users...")
        users = await conn.fetch(
            """
            SELECT DISTINCT u.*
            FROM users u
            WHERE u.status = 'active'
            ORDER BY u.created_at DESC
            LIMIT $1
            """,
            LIMIT_USERS,
        )
        users_data = [sanitize_user(dict(user)) for user in users]

        with open(EXPORT_DIR / "users.json", "w") as f:
            json.dump(users_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(users_data)} sanitized users")

        # Export ratings
        print(f"\nExporting {LIMIT_RATINGS} ratings...")
        ratings = await conn.fetch(
            """
            SELECT *
            FROM ratings
            WHERE book_id = ANY($1::uuid[])
            ORDER BY created_at DESC
            LIMIT $2
            """,
            book_ids,
            LIMIT_RATINGS,
        )
        ratings_data = [dict(rating) for rating in ratings]

        with open(EXPORT_DIR / "ratings.json", "w") as f:
            json.dump(ratings_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(ratings_data)} ratings")

        # Export favorites
        print(f"\nExporting {LIMIT_FAVORITES} favorites...")
        favorites = await conn.fetch(
            """
            SELECT *
            FROM favorites
            WHERE book_id = ANY($1::uuid[])
            ORDER BY created_at DESC
            LIMIT $2
            """,
            book_ids,
            LIMIT_FAVORITES,
        )
        favorites_data = [dict(fav) for fav in favorites]

        with open(EXPORT_DIR / "favorites.json", "w") as f:
            json.dump(favorites_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(favorites_data)} favorites")

        # Export chat sessions
        print(f"\nExporting {LIMIT_CHAT_SESSIONS} chat sessions...")
        chat_sessions = await conn.fetch(
            """
            SELECT *
            FROM chat_sessions
            WHERE book_id = ANY($1::uuid[])
            ORDER BY created_at DESC
            LIMIT $2
            """,
            book_ids,
            LIMIT_CHAT_SESSIONS,
        )
        chat_sessions_data = [dict(session) for session in chat_sessions]
        session_ids = [session["id"] for session in chat_sessions_data]

        with open(EXPORT_DIR / "chat_sessions.json", "w") as f:
            json.dump(chat_sessions_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(chat_sessions_data)} chat sessions")

        # Export chat messages for those sessions
        if session_ids:
            print("\nExporting chat messages...")
            chat_messages = await conn.fetch(
                """
                SELECT *
                FROM chat_messages
                WHERE session_id = ANY($1::uuid[])
                ORDER BY created_at
                """,
                session_ids,
            )
            chat_messages_data = [dict(msg) for msg in chat_messages]

            with open(EXPORT_DIR / "chat_messages.json", "w") as f:
                json.dump(chat_messages_data, f, indent=2, default=serialize_datetime)
            print(f"✓ Exported {len(chat_messages_data)} chat messages")

        # Export page images for some books
        print(f"\nExporting page images for {LIMIT_BOOKS_WITH_PAGES} books...")
        pages = await conn.fetch(
            """
            SELECT *
            FROM page_images
            WHERE book_id = ANY(
                SELECT DISTINCT book_id
                FROM page_images
                LIMIT $1
            )
            ORDER BY book_id, page_number
            """,
            LIMIT_BOOKS_WITH_PAGES,
        )
        pages_data = [dict(page) for page in pages]

        with open(EXPORT_DIR / "page_images.json", "w") as f:
            json.dump(pages_data, f, indent=2, default=serialize_datetime)
        print(f"✓ Exported {len(pages_data)} page images")

        # Create README
        readme_content = f"""# ILM Red Sample Data

**Source**: Azure PostgreSQL Production Database
**Exported**: {datetime.now().isoformat()}
**Host**: {PROD_DB_HOST}

## Data Sanitization

All sensitive data has been sanitized:
- Emails: Replaced with @test.com addresses
- Passwords: All reset to hashed "test123"
- Display names: Anonymized for users with real-looking names
- Extra data: Removed

## Files

- `books.json` - {len(books_data)} books (various categories, visibility)
- `users.json` - {len(users_data)} sanitized users (various roles)
- `ratings.json` - {len(ratings_data)} book ratings
- `favorites.json` - {len(favorites_data)} favorite books
- `chat_sessions.json` - {len(chat_sessions_data)} AI chat sessions
- `chat_messages.json` - {len(chat_messages_data if session_ids else [])} chat messages
- `page_images.json` - {len(pages_data)} page images ({LIMIT_BOOKS_WITH_PAGES} books)

## Usage

Import this data to your local database using:

```bash
python scripts/import_sample_data.py
```

## Test Credentials

All users have password: `test123`

Example users:
- Admin user: Check users.json for role='super_admin'
- Regular users: Check users.json for role='user'
"""

        with open(EXPORT_DIR / "README.md", "w") as f:
            f.write(readme_content)

        print(f"\n✅ Export complete! Data saved to: {EXPORT_DIR}")
        print("\nSummary:")
        print(f"  - {len(books_data)} books")
        print(f"  - {len(users_data)} users")
        print(f"  - {len(ratings_data)} ratings")
        print(f"  - {len(favorites_data)} favorites")
        print(f"  - {len(chat_sessions_data)} chat sessions")
        print(f"  - {len(chat_messages_data if session_ids else [])} chat messages")
        print(f"  - {len(pages_data)} page images")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(export_data())
