#!/usr/bin/env python3
"""Migrate enhanced chat data from Supabase to API PostgreSQL.

This extends the basic chat migration with the new Wave-6 columns:
  ai_model, ai_provider, session_type, category, expert_id, is_public,
  is_archived, system_prompt, configuration, book_club_id, etc.

Tables migrated:
  book_chat_sessions  -> chat_sessions
  book_chat_messages  -> chat_messages
  chat_message_ratings -> chat_message_ratings
  chat_admin_access_log -> chat_admin_access_log (if exists)
  session_analytics   -> session_analytics (if exists)

Usage:
    python scripts/migrations/06_migrate_chat.py
    python scripts/migrations/06_migrate_chat.py --dry-run
    python scripts/migrations/06_migrate_chat.py --export-only

Environment variables:
    SUPABASE_DB_URL: Supabase PostgreSQL connection URL
    TARGET_DATABASE_URL: Target PostgreSQL connection URL
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Common utilities
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from _common import (
    BATCH_SIZE,
    MigrationStats,
    connect_source,
    connect_target,
    fetch_paginated,
    get_valid_book_ids,
    get_valid_user_ids,
    parse_dt,
    safe_uuid,
    save_export,
    table_exists,
)

# ---------------------------------------------------------------------------
# Role mapping
# ---------------------------------------------------------------------------
ROLE_MAP = {
    "user": "user",
    "ai": "assistant",
    "system": "system",
    "assistant": "assistant",
}


def _is_encrypted(content: str | None) -> bool:
    """Heuristic: detect if content looks encrypted / base64-encoded."""
    if not content:
        return False
    # Encrypted messages are typically long base64 blobs with no whitespace
    if len(content) > 200 and " " not in content[:200] and "\n" not in content[:200]:
        return True
    return False


# ========================================================================
# Chat sessions
# ========================================================================


async def migrate_chat_sessions(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    valid_book_ids: set[str],
    dry_run: bool,
) -> set[str]:
    """Migrate book_chat_sessions -> chat_sessions with enhanced columns."""
    src_table = "book_chat_sessions"
    tgt_table = "chat_sessions"
    print(f"\nMigrating {src_table} -> {tgt_table}...")

    if not await table_exists(source, src_table):
        print(f"  Source table {src_table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(
        source,
        f"SELECT * FROM {src_table} WHERE user_id IS NOT NULL ORDER BY id",
    )
    valid_session_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {src_table}")
        return valid_session_ids

    stats.track(tgt_table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {tgt_table}"):
        row_id = str(row["id"])
        user_id = str(row["user_id"]) if row.get("user_id") else None

        if not user_id or user_id not in valid_user_ids:
            stats.track(tgt_table, skipped=1)
            continue

        # Book is optional; clear if invalid
        book_id = str(row["book_id"]) if row.get("book_id") else None
        if book_id and book_id not in valid_book_ids:
            book_id = None

        valid_session_ids.add(row_id)

        if dry_run:
            stats.track(tgt_table, imported=1)
            continue

        # Map fields
        title = row.get("session_name")
        ai_model = row.get("ai_model")
        ai_provider = row.get("ai_provider")
        session_type = row.get("session_type")
        category = row.get("category")
        expert_id = row.get("expert_id")
        is_public = row.get("is_public", False)
        is_archived = row.get("is_archived", False)
        book_club_id = row.get("book_club_id")
        message_count = row.get("message_count", 0)
        created_at = parse_dt(row.get("created_at"))
        updated_at = parse_dt(row.get("updated_at"))

        # Map is_archived -> archived_at
        archived_at = updated_at if is_archived else None

        # Configuration JSONB
        configuration = row.get("configuration")
        if isinstance(configuration, str):
            try:
                configuration = json.loads(configuration)
            except (json.JSONDecodeError, TypeError):
                configuration = None
        config_json = json.dumps(configuration) if configuration else None

        try:
            await target.execute(
                """
                INSERT INTO chat_sessions (
                    id, user_id, book_id, title, message_count, last_model,
                    archived_at, ai_model, ai_provider, session_type, category,
                    expert_id, is_public, is_archived,
                    configuration, book_club_id,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10, $11,
                    $12, $13, $14,
                    $15, $16,
                    $17, $18
                )
                ON CONFLICT (id) DO UPDATE SET
                    ai_model = EXCLUDED.ai_model,
                    ai_provider = EXCLUDED.ai_provider,
                    session_type = EXCLUDED.session_type,
                    category = EXCLUDED.category,
                    expert_id = EXCLUDED.expert_id,
                    is_public = EXCLUDED.is_public,
                    is_archived = EXCLUDED.is_archived,
                    archived_at = EXCLUDED.archived_at,
                    configuration = EXCLUDED.configuration,
                    book_club_id = EXCLUDED.book_club_id,
                    updated_at = EXCLUDED.updated_at
                """,
                safe_uuid(row_id),
                safe_uuid(user_id),
                safe_uuid(book_id),
                title,
                message_count,
                ai_model,              # last_model = ai_model for now
                archived_at,
                ai_model,
                ai_provider,
                session_type,
                category,
                safe_uuid(str(expert_id)) if expert_id else None,
                is_public,
                is_archived,
                config_json,
                safe_uuid(str(book_club_id)) if book_club_id else None,
                created_at,
                updated_at,
            )
            stats.track(tgt_table, imported=1)
        except Exception as e:
            stats.track(tgt_table, skipped=1)
            stats.errors.append(f"{tgt_table} {row_id}: {e}")

    print(f"  {tgt_table}: {stats.tables[tgt_table]}")
    return valid_session_ids


# ========================================================================
# Chat messages
# ========================================================================


async def migrate_chat_messages(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_session_ids: set[str],
    dry_run: bool,
) -> set[str]:
    """Migrate book_chat_messages -> chat_messages with role mapping.

    Encrypted messages are skipped gracefully.
    """
    src_table = "book_chat_messages"
    tgt_table = "chat_messages"
    print(f"\nMigrating {src_table} -> {tgt_table}...")

    if not await table_exists(source, src_table):
        print(f"  Source table {src_table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(
        source,
        f"SELECT * FROM {src_table} ORDER BY session_id, created_at",
    )
    valid_message_ids: set[str] = set()
    encrypted_skipped = 0

    if not rows:
        print(f"  No rows found in {src_table}")
        return valid_message_ids

    stats.track(tgt_table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {tgt_table}"):
        row_id = str(row["id"])
        session_id = str(row["session_id"]) if row.get("session_id") else None

        if not session_id or session_id not in valid_session_ids:
            stats.track(tgt_table, skipped=1)
            continue

        # Get content - handle encrypted messages
        content = row.get("content") or ""
        if _is_encrypted(content):
            encrypted_skipped += 1
            stats.track(tgt_table, skipped=1)
            continue

        if not content:
            stats.track(tgt_table, skipped=1)
            continue

        # Map role
        src_type = row.get("message_type", "user")
        role = ROLE_MAP.get(src_type, "user")

        valid_message_ids.add(row_id)

        if dry_run:
            stats.track(tgt_table, imported=1)
            continue

        # Metadata
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = None
        metadata_json = json.dumps(metadata) if metadata else None

        # Context from source could contain model info
        context = row.get("context")
        if isinstance(context, str):
            try:
                context = json.loads(context)
            except (json.JSONDecodeError, TypeError):
                context = None

        # Try to extract model name from context or metadata
        model = None
        if context and isinstance(context, dict):
            model = context.get("model") or context.get("ai_model")
        if not model and metadata and isinstance(metadata, dict):
            model = metadata.get("model") or metadata.get("ai_model")

        is_sensitive = row.get("is_sensitive", False)

        try:
            await target.execute(
                """
                INSERT INTO chat_messages (
                    id, session_id, role, content, model,
                    tokens_input, tokens_output, cost_cents,
                    is_sensitive, metadata_json, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row_id),
                safe_uuid(session_id),
                role,
                content,
                model,
                None,  # tokens_input - not available in source
                None,  # tokens_output - not available in source
                None,  # cost_cents - not available in source
                is_sensitive,
                metadata_json,
                parse_dt(row.get("created_at")),
            )
            stats.track(tgt_table, imported=1)
        except Exception as e:
            stats.track(tgt_table, skipped=1)
            stats.errors.append(f"{tgt_table} {row_id}: {e}")

    if encrypted_skipped:
        print(f"  Skipped {encrypted_skipped} encrypted messages")
    print(f"  {tgt_table}: {stats.tables[tgt_table]}")
    return valid_message_ids


# ========================================================================
# Chat message ratings
# ========================================================================


async def migrate_chat_message_ratings(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_message_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate chat_message_ratings."""
    table = "chat_message_ratings"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        message_id = str(row["message_id"]) if row.get("message_id") else None
        user_id = str(row["user_id"]) if row.get("user_id") else None

        if not message_id or message_id not in valid_message_ids:
            stats.track(table, skipped=1)
            continue
        if not user_id or user_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO chat_message_ratings (id, message_id, user_id, rating,
                    feedback, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row_id),
                safe_uuid(message_id),
                safe_uuid(user_id),
                row.get("rating"),
                row.get("feedback"),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Chat admin access log
# ========================================================================


async def migrate_chat_admin_access_log(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_session_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate chat_admin_access_log (if exists)."""
    table = "chat_admin_access_log"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    if not await table_exists(target, table):
        print(f"  Target table {table} does not exist - skipping")
        return

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        session_id = str(row["session_id"]) if row.get("session_id") else None
        admin_id = str(row["admin_id"]) if row.get("admin_id") else None

        if session_id and session_id not in valid_session_ids:
            stats.track(table, skipped=1)
            continue
        if admin_id and admin_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO chat_admin_access_log (id, session_id, admin_id,
                    action, reason, ip_address, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row_id),
                safe_uuid(session_id),
                safe_uuid(admin_id),
                row.get("action"),
                row.get("reason"),
                row.get("ip_address"),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Session analytics
# ========================================================================


async def migrate_session_analytics(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_session_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate session_analytics (if exists)."""
    table = "session_analytics"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    if not await table_exists(target, table):
        print(f"  Target table {table} does not exist - skipping")
        return

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        session_id = str(row["session_id"]) if row.get("session_id") else None

        if session_id and session_id not in valid_session_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            # Build dynamic insert from row columns
            cols = list(row.keys())
            placeholders = [f"${i+1}" for i in range(len(cols))]
            values = []
            for col in cols:
                val = row[col]
                if col.endswith("_id") or col == "id":
                    val = safe_uuid(val)
                elif col.endswith("_at"):
                    val = parse_dt(val)
                elif isinstance(val, dict):
                    val = json.dumps(val)
                values.append(val)

            col_str = ", ".join(cols)
            ph_str = ", ".join(placeholders)

            await target.execute(
                f"INSERT INTO {table} ({col_str}) VALUES ({ph_str}) ON CONFLICT (id) DO NOTHING",
                *values,
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Main
# ========================================================================


async def main(dry_run: bool = False, export_only: bool = False) -> int:
    """Run enhanced chat migration."""
    print("\n" + "=" * 60)
    print("MIGRATION 06: Enhanced Chat (sessions, messages, ratings)")
    print("=" * 60)
    mode = "DRY RUN" if dry_run else ("EXPORT ONLY" if export_only else "LIVE")
    print(f"Mode: {mode}")
    print("=" * 60)

    stats = MigrationStats("06_chat")
    source = await connect_source()

    try:
        target = None
        if not export_only:
            target = await connect_target()

        # Build valid FK sets from target
        valid_user_ids: set[str] = set()
        valid_book_ids: set[str] = set()
        if target:
            valid_user_ids = await get_valid_user_ids(target)
            valid_book_ids = await get_valid_book_ids(target)
            print(f"  Found {len(valid_user_ids)} valid users in target")
            print(f"  Found {len(valid_book_ids)} valid books in target")

        effective_dry = dry_run or export_only

        # Sessions
        valid_session_ids = await migrate_chat_sessions(
            source, target, stats, valid_user_ids, valid_book_ids, effective_dry,
        )

        # Messages
        valid_message_ids = await migrate_chat_messages(
            source, target, stats, valid_session_ids, effective_dry,
        )

        # Ratings
        await migrate_chat_message_ratings(
            source, target, stats, valid_message_ids, valid_user_ids, effective_dry,
        )

        # Admin access log (optional table)
        await migrate_chat_admin_access_log(
            source, target, stats, valid_session_ids, valid_user_ids, effective_dry,
        )

        # Session analytics (optional table)
        await migrate_session_analytics(
            source, target, stats, valid_session_ids, effective_dry,
        )

    finally:
        await source.close()
        if target:
            await target.close()

    stats.print_summary()
    return 0 if not stats.errors else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate enhanced chat data from Supabase to API DB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    parser.add_argument("--export-only", action="store_true", help="Only export/count, no import")
    args = parser.parse_args()

    exit_code = asyncio.run(main(dry_run=args.dry_run, export_only=args.export_only))
    sys.exit(exit_code)
