#!/usr/bin/env python3
"""Import seed data into local database.

This script imports JSON seed files into the local database for
development and testing purposes.

Usage:
    python scripts/import_test_data.py [--clear]

Options:
    --clear: Clear existing data before importing

Environment variables:
    DATABASE_URL: Database connection string
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

SEEDS_DIR = Path(__file__).parent.parent / "seeds"

# Default database URL for local development
DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ilmred"
)


async def get_session(database_url: str) -> AsyncSession:
    """Create database session.

    Args:
        database_url: Database connection string

    Returns:
        Async database session
    """
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return async_session()


async def clear_data(session: AsyncSession) -> None:
    """Clear existing data from tables.

    Args:
        session: Database session
    """
    print("Clearing existing data...")

    # Order matters due to foreign keys
    tables = [
        "message_feedback",
        "chat_messages",
        "chat_sessions",
        "billing_transactions",
        "user_credits",
        "usage_limits",
        "safety_flags",
        "favorites",
        "ratings",
        "books",
    ]

    for table in tables:
        try:
            await session.execute(text(f"DELETE FROM {table}"))
            print(f"  Cleared {table}")
        except Exception as e:
            print(f"  Skipped {table}: {e}")

    await session.commit()
    print()


async def import_books(session: AsyncSession) -> int:
    """Import books from seed file.

    Args:
        session: Database session

    Returns:
        Number of books imported
    """
    seed_file = SEEDS_DIR / "books.json"
    if not seed_file.exists():
        print("  No books.json found, skipping")
        return 0

    print("Importing books...")

    data = json.loads(seed_file.read_text())
    items = data.get("items", [])

    imported = 0
    for item in items:
        try:
            # Generate new UUID for local DB
            book_id = str(uuid4())

            # Build insert statement
            await session.execute(
                text("""
                    INSERT INTO books (
                        id, owner_id, title, author, description,
                        category, language, visibility, page_count,
                        file_size, file_hash, status, thumbnail_url,
                        created_at, updated_at
                    ) VALUES (
                        :id, :owner_id, :title, :author, :description,
                        :category, :language, :visibility, :page_count,
                        :file_size, :file_hash, :status, :thumbnail_url,
                        :created_at, :updated_at
                    )
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": book_id,
                    "owner_id": item.get("owner_id") or str(uuid4()),  # Dummy owner
                    "title": item.get("title", "Untitled"),
                    "author": item.get("author"),
                    "description": item.get("description"),
                    "category": item.get("category", "Other"),
                    "language": item.get("language", "en"),
                    "visibility": "public",  # All imported books are public
                    "page_count": item.get("page_count", 0),
                    "file_size": item.get("file_size", 0),
                    "file_hash": item.get("file_hash") or f"hash_{uuid4().hex[:16]}",
                    "status": "ready",
                    "thumbnail_url": item.get("thumbnail_url"),
                    "created_at": datetime.now(UTC),
                    "updated_at": datetime.now(UTC),
                },
            )
            imported += 1
        except Exception as e:
            print(f"    Error importing book '{item.get('title', 'unknown')}': {e}")

    await session.commit()
    print(f"  Imported {imported} books")
    return imported


async def create_test_user(session: AsyncSession) -> str:
    """Create a test user for local development.

    Args:
        session: Database session

    Returns:
        Test user ID
    """
    print("Creating test user...")

    user_id = str(uuid4())

    try:
        await session.execute(
            text("""
                INSERT INTO users (
                    id, email, display_name, password_hash,
                    roles, preferences, created_at, updated_at
                ) VALUES (
                    :id, :email, :display_name, :password_hash,
                    :roles, :preferences, :created_at, :updated_at
                )
                ON CONFLICT (email) DO UPDATE SET
                    roles = :roles,
                    updated_at = :updated_at
                RETURNING id
            """),
            {
                "id": user_id,
                "email": "test@ilmred.dev",
                "display_name": "Test User",
                "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$dummy$hash",  # Not valid, use /auth/register
                "roles": ["user", "admin"],  # Admin for testing
                "preferences": json.dumps({"theme": "light", "language": "en"}),
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        await session.commit()
        print(f"  Created test user: test@ilmred.dev (id: {user_id})")
        print("  Note: Use /auth/register to create a user with valid password")
        return user_id
    except Exception as e:
        print(f"  Test user may already exist: {e}")
        # Return existing user ID
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'test@ilmred.dev'")
        )
        row = result.fetchone()
        return str(row[0]) if row else user_id


async def initialize_billing(session: AsyncSession, user_id: str) -> None:
    """Initialize billing records for test user.

    Args:
        session: Database session
        user_id: User ID
    """
    print("Initializing billing...")

    try:
        # Create user credits
        await session.execute(
            text("""
                INSERT INTO user_credits (
                    user_id, balance_cents, lifetime_usage_cents,
                    free_credits_remaining, updated_at
                ) VALUES (
                    :user_id, 10000, 0, 100, :updated_at
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    balance_cents = 10000,
                    free_credits_remaining = 100,
                    updated_at = :updated_at
            """),
            {
                "user_id": user_id,
                "updated_at": datetime.now(UTC),
            },
        )

        # Create usage limits
        await session.execute(
            text("""
                INSERT INTO usage_limits (
                    user_id, daily_tokens_limit, daily_tokens_used,
                    monthly_cost_limit_cents, monthly_cost_used_cents
                ) VALUES (
                    :user_id, 100000, 0, 10000, 0
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    daily_tokens_limit = 100000,
                    monthly_cost_limit_cents = 10000
            """),
            {
                "user_id": user_id,
            },
        )

        await session.commit()
        print("  Initialized billing with 100 free credits")
    except Exception as e:
        print(f"  Billing initialization error: {e}")


async def main(clear: bool) -> int:
    """Main import function.

    Args:
        clear: Whether to clear existing data first

    Returns:
        Exit code (0 for success)
    """
    print("\nILM Red API - Data Import")
    print(f"{'=' * 50}")
    print(f"Database: {DEFAULT_DATABASE_URL.split('@')[1] if '@' in DEFAULT_DATABASE_URL else 'local'}")
    print(f"Seeds: {SEEDS_DIR}")
    print()

    # Check seeds directory
    if not SEEDS_DIR.exists():
        print("Seeds directory not found. Run export_test_data.py first.")
        return 1

    try:
        async with await get_session(DEFAULT_DATABASE_URL) as session:
            # Clear data if requested
            if clear:
                await clear_data(session)

            # Import data
            await import_books(session)

            # Create test user
            user_id = await create_test_user(session)

            # Initialize billing
            await initialize_billing(session, user_id)

            print()
            print(f"{'=' * 50}")
            print("Import complete!")
            print()
            print("Test credentials:")
            print("  Email: test@ilmred.dev")
            print("  Note: Register a new user with /auth/register for valid login")
            print()
            print("To start the API locally, run:")
            print("  cd docker && docker compose up")

            return 0
    except Exception as e:
        print(f"Database error: {e}")
        print()
        print("Make sure the database is running:")
        print("  cd docker && docker compose up -d db")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import seed data into local database"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before importing",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(args.clear))
    sys.exit(exit_code)
