#!/usr/bin/env python3
"""Import sample data from data/ directory into local database.

This script imports:
- Users
- Books
- Ratings
- Favorites
- Chat sessions and messages
- Page images

Usage:
    poetry run python scripts/import_sample_data.py
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"


async def import_data():
    """Import sample data into local database."""
    print("Connecting to local database...")

    engine = create_async_engine(str(settings.database_url), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Check if tables are empty
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()

            if user_count > 0:
                print(f"\n⚠️  Warning: Database already has {user_count} users")
                response = input("Do you want to continue? This will add more data. (y/N): ")
                if response.lower() != "y":
                    print("Aborted.")
                    return

            # Import users
            users_file = DATA_DIR / "users.json"
            if users_file.exists():
                with open(users_file) as f:
                    users = json.load(f)

                print(f"\nImporting {len(users)} users...")
                for user in users:
                    # Convert string UUIDs back to proper format
                    await session.execute(
                        text(
                            """
                            INSERT INTO users (
                                id, email, email_verified, username, display_name,
                                password_hash, avatar_url, bio, roles, status,
                                preferences, created_at, last_login_at
                            ) VALUES (
                                :id, :email, :email_verified, :username, :display_name,
                                :password_hash, :avatar_url, :bio, :roles, :status,
                                :preferences, :created_at, :last_login_at
                            )
                            ON CONFLICT (id) DO NOTHING
                            """
                        ),
                        {
                            "id": user["id"],
                            "email": user["email"],
                            "email_verified": user.get("email_verified", True),
                            "username": user["username"],
                            "display_name": user.get("display_name", user["username"]),
                            "password_hash": user["password_hash"],
                            "avatar_url": user.get("avatar_url"),
                            "bio": user.get("bio"),
                            "roles": user.get("roles", ["user"]),
                            "status": user.get("status", "active"),
                            "preferences": user.get("preferences", {}),
                            "created_at": user["created_at"],
                            "last_login_at": user.get("last_login_at"),
                        },
                    )
                await session.commit()
                print(f"✓ Imported {len(users)} users")

            # Import books
            books_file = DATA_DIR / "books.json"
            if books_file.exists():
                with open(books_file) as f:
                    books = json.load(f)

                print(f"\nImporting {len(books)} books...")
                for book in books:
                    await session.execute(
                        text(
                            """
                            INSERT INTO books (
                                id, owner_id, title, author, description, category,
                                language, isbn, visibility, file_path, file_hash,
                                file_size, file_type, original_filename, page_count,
                                cover_url, status, processing_error, stats,
                                created_at, updated_at, deleted_at
                            ) VALUES (
                                :id, :owner_id, :title, :author, :description, :category,
                                :language, :isbn, :visibility, :file_path, :file_hash,
                                :file_size, :file_type, :original_filename, :page_count,
                                :cover_url, :status, :processing_error, :stats,
                                :created_at, :updated_at, :deleted_at
                            )
                            ON CONFLICT (id) DO NOTHING
                            """
                        ),
                        {
                            "id": book["id"],
                            "owner_id": book["owner_id"],
                            "title": book["title"],
                            "author": book.get("author"),
                            "description": book.get("description"),
                            "category": book["category"],
                            "language": book.get("language", "en"),
                            "isbn": book.get("isbn"),
                            "visibility": book["visibility"],
                            "file_path": book["file_path"],
                            "file_hash": book["file_hash"],
                            "file_size": book["file_size"],
                            "file_type": book["file_type"],
                            "original_filename": book.get("original_filename"),
                            "page_count": book.get("page_count"),
                            "cover_url": book.get("cover_url"),
                            "status": book.get("status", "ready"),
                            "processing_error": book.get("processing_error"),
                            "stats": book.get("stats", {}),
                            "created_at": book["created_at"],
                            "updated_at": book.get("updated_at"),
                            "deleted_at": book.get("deleted_at"),
                        },
                    )
                await session.commit()
                print(f"✓ Imported {len(books)} books")

            # Import ratings
            ratings_file = DATA_DIR / "ratings.json"
            if ratings_file.exists():
                with open(ratings_file) as f:
                    ratings = json.load(f)

                print(f"\nImporting {len(ratings)} ratings...")
                for rating in ratings:
                    await session.execute(
                        text(
                            """
                            INSERT INTO ratings (
                                id, book_id, user_id, rating, review,
                                created_at, updated_at
                            ) VALUES (
                                :id, :book_id, :user_id, :rating, :review,
                                :created_at, :updated_at
                            )
                            ON CONFLICT (book_id, user_id) DO NOTHING
                            """
                        ),
                        {
                            "id": rating["id"],
                            "book_id": rating["book_id"],
                            "user_id": rating["user_id"],
                            "rating": rating["rating"],
                            "review": rating.get("review"),
                            "created_at": rating["created_at"],
                            "updated_at": rating["updated_at"],
                        },
                    )
                await session.commit()
                print(f"✓ Imported {len(ratings)} ratings")

            # Import favorites
            favorites_file = DATA_DIR / "favorites.json"
            if favorites_file.exists():
                with open(favorites_file) as f:
                    favorites = json.load(f)

                print(f"\nImporting {len(favorites)} favorites...")
                for fav in favorites:
                    await session.execute(
                        text(
                            """
                            INSERT INTO favorites (
                                user_id, book_id, created_at
                            ) VALUES (
                                :user_id, :book_id, :created_at
                            )
                            ON CONFLICT (user_id, book_id) DO NOTHING
                            """
                        ),
                        {
                            "user_id": fav["user_id"],
                            "book_id": fav["book_id"],
                            "created_at": fav["created_at"],
                        },
                    )
                await session.commit()
                print(f"✓ Imported {len(favorites)} favorites")

            # Import chat sessions
            chat_sessions_file = DATA_DIR / "chat_sessions.json"
            if chat_sessions_file.exists():
                with open(chat_sessions_file) as f:
                    sessions = json.load(f)

                print(f"\nImporting {len(sessions)} chat sessions...")
                for sess in sessions:
                    await session.execute(
                        text(
                            """
                            INSERT INTO chat_sessions (
                                id, user_id, book_id, title, model, message_count,
                                total_tokens, total_cost_cents, created_at, updated_at
                            ) VALUES (
                                :id, :user_id, :book_id, :title, :model, :message_count,
                                :total_tokens, :total_cost_cents, :created_at, :updated_at
                            )
                            ON CONFLICT (id) DO NOTHING
                            """
                        ),
                        {
                            "id": sess["id"],
                            "user_id": sess["user_id"],
                            "book_id": sess.get("book_id"),
                            "title": sess.get("title"),
                            "model": sess.get("model"),
                            "message_count": sess.get("message_count", 0),
                            "total_tokens": sess.get("total_tokens", 0),
                            "total_cost_cents": sess.get("total_cost_cents", 0),
                            "created_at": sess["created_at"],
                            "updated_at": sess.get("updated_at"),
                        },
                    )
                await session.commit()
                print(f"✓ Imported {len(sessions)} chat sessions")

            # Import chat messages
            chat_messages_file = DATA_DIR / "chat_messages.json"
            if chat_messages_file.exists():
                with open(chat_messages_file) as f:
                    messages = json.load(f)

                if messages:
                    print(f"\nImporting {len(messages)} chat messages...")
                    for msg in messages:
                        await session.execute(
                            text(
                                """
                                INSERT INTO chat_messages (
                                    id, session_id, role, content, model, tokens,
                                    cost_cents, created_at
                                ) VALUES (
                                    :id, :session_id, :role, :content, :model, :tokens,
                                    :cost_cents, :created_at
                                )
                                ON CONFLICT (id) DO NOTHING
                                """
                            ),
                            {
                                "id": msg["id"],
                                "session_id": msg["session_id"],
                                "role": msg["role"],
                                "content": msg["content"],
                                "model": msg.get("model"),
                                "tokens": msg.get("tokens", 0),
                                "cost_cents": msg.get("cost_cents", 0),
                                "created_at": msg["created_at"],
                            },
                        )
                    await session.commit()
                    print(f"✓ Imported {len(messages)} chat messages")

            # Import page images
            pages_file = DATA_DIR / "page_images.json"
            if pages_file.exists():
                with open(pages_file) as f:
                    pages = json.load(f)

                if pages:
                    print(f"\nImporting {len(pages)} page images...")
                    for page in pages:
                        await session.execute(
                            text(
                                """
                                INSERT INTO page_images (
                                    id, book_id, page_number, width, height,
                                    thumbnail_path, medium_path, created_at
                                ) VALUES (
                                    :id, :book_id, :page_number, :width, :height,
                                    :thumbnail_path, :medium_path, :created_at
                                )
                                ON CONFLICT (book_id, page_number) DO NOTHING
                                """
                            ),
                            {
                                "id": page["id"],
                                "book_id": page["book_id"],
                                "page_number": page["page_number"],
                                "width": page["width"],
                                "height": page["height"],
                                "thumbnail_path": page.get("thumbnail_path"),
                                "medium_path": page.get("medium_path"),
                                "created_at": page["created_at"],
                            },
                        )
                    await session.commit()
                    print(f"✓ Imported {len(pages)} page images")

            print("\n✅ Import complete!")
            print("\nTest credentials: All users have password 'test123'")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_data())
