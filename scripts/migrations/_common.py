"""Common utilities for Supabase -> API data migration scripts."""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg
from tqdm import tqdm

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
TARGET_DB_URL = os.getenv("TARGET_DATABASE_URL", "")
BATCH_SIZE = 1000

# Paths
SCRIPT_DIR = Path(__file__).parent
EXPORT_DIR = SCRIPT_DIR.parent.parent / "exports" / "supabase_migration"


class MigrationStats:
    """Track migration statistics per table."""

    def __init__(self, name: str):
        self.name = name
        self.tables: dict[str, dict] = {}
        self.errors: list[str] = []

    def track(self, table: str, exported: int = 0, imported: int = 0, skipped: int = 0):
        if table not in self.tables:
            self.tables[table] = {"exported": 0, "imported": 0, "skipped": 0}
        self.tables[table]["exported"] += exported
        self.tables[table]["imported"] += imported
        self.tables[table]["skipped"] += skipped

    def print_summary(self):
        print(f"\n{'=' * 60}")
        print(f"MIGRATION SUMMARY: {self.name}")
        print(f"{'=' * 60}")
        for table, counts in self.tables.items():
            print(
                f"  {table:40s} exported={counts['exported']:>6d}"
                f"  imported={counts['imported']:>6d}"
                f"  skipped={counts['skipped']:>6d}"
            )
        if self.errors:
            print(f"\n  Errors: {len(self.errors)}")
            for err in self.errors[:10]:
                print(f"    - {err}")
            if len(self.errors) > 10:
                print(f"    ... and {len(self.errors) - 10} more")
        print(f"{'=' * 60}")


async def connect_source() -> asyncpg.Connection:
    """Connect to Supabase PostgreSQL."""
    print("Connecting to Supabase PostgreSQL...")
    conn = await asyncpg.connect(SUPABASE_DB_URL, ssl="require", statement_cache_size=0)
    print("  Connected!")
    return conn


async def connect_target() -> asyncpg.Connection:
    """Connect to target PostgreSQL."""
    print("Connecting to target PostgreSQL...")
    url = TARGET_DB_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    print("  Connected!")
    return conn


async def fetch_paginated(
    conn: asyncpg.Connection, query: str, batch_size: int = BATCH_SIZE
) -> list[asyncpg.Record]:
    """Fetch all rows from a query using LIMIT/OFFSET pagination."""
    all_rows: list[asyncpg.Record] = []
    offset = 0
    while True:
        paginated_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
        rows = await conn.fetch(paginated_query)
        if not rows:
            break
        all_rows.extend(rows)
        offset += batch_size
    return all_rows


async def table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
        table_name,
    )
    return result


async def get_valid_user_ids(target: asyncpg.Connection) -> set[str]:
    """Get all valid user IDs from target database."""
    rows = await target.fetch("SELECT id FROM users")
    return {str(row["id"]) for row in rows}


async def get_valid_book_ids(target: asyncpg.Connection) -> set[str]:
    """Get all valid book IDs from target database."""
    rows = await target.fetch("SELECT id FROM books")
    return {str(row["id"]) for row in rows}


def parse_dt(value) -> datetime | None:
    """Parse a datetime value from a database row."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def safe_uuid(value) -> UUID | None:
    """Safely convert a value to UUID."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def save_export(data: dict, name: str) -> None:
    """Save exported data to JSON file."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EXPORT_DIR / f"{name}.json"
    output_file.write_text(json.dumps(data, indent=2, default=str))
    print(f"  Saved to {output_file}")
