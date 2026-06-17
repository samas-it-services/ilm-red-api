#!/usr/bin/env python3
"""Migrate book club data (17 tables) from Supabase to API PostgreSQL.

Tables migrated in FK order:
 1. book_clubs
 2. book_club_members
 3. book_club_books
 4. book_club_discussions
 5. book_club_discussion_replies
 6. book_club_invites
 7. book_club_activities
 8. book_club_challenges
 9. book_club_challenge_participants
10. book_club_nominations
11. book_club_votes
12. book_club_notifications
13. book_club_poster_history
14. book_club_exclusive_books
15. book_club_member_stats
16. book_club_achievements
17. book_club_member_achievements

Usage:
    python scripts/migrations/03_migrate_clubs.py
    python scripts/migrations/03_migrate_clubs.py --dry-run
    python scripts/migrations/03_migrate_clubs.py --export-only
    python scripts/migrations/03_migrate_clubs.py --skip-import

Environment variables:
    SUPABASE_DB_URL: Supabase direct PostgreSQL connection string
    TARGET_DATABASE_URL: Target PostgreSQL URL
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

# Add parent to path so we can import _common
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.migrations._common import (
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
# Generic helpers
# ---------------------------------------------------------------------------

async def export_table(
    source: asyncpg.Connection,
    table: str,
    query: str,
    stats: MigrationStats,
    label: str | None = None,
) -> list[asyncpg.Record]:
    """Generic paginated export from a Supabase table."""
    label = label or table
    print(f"\nExporting {label}...")

    if not await table_exists(source, table):
        print(f"  {table} table not found in source, skipping")
        return []

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    stats.track(table, exported=len(rows))
    print(f"  Exported {len(rows)} rows from {table}")
    return rows


def row_to_dict(row: asyncpg.Record) -> dict:
    """Convert an asyncpg Record to a plain dict with str UUIDs."""
    d: dict = {}
    for key in row.keys():
        val = row[key]
        if isinstance(val, UUID):
            d[key] = str(val)
        elif isinstance(val, datetime):
            d[key] = val.isoformat()
        else:
            d[key] = val
    return d


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

async def export_all(source: asyncpg.Connection, stats: MigrationStats) -> dict[str, list]:
    """Export all book-club-related tables from Supabase."""
    data: dict[str, list] = {}

    # 1. book_clubs
    rows = await export_table(source, "book_clubs", """
        SELECT id, name, description, tagline, summary, welcome_message,
               cover_image_url, cover_thumbnail_url, owner_id,
               visibility, club_type, max_members, member_limit,
               is_premium_only, featured_book_id, settings, premium_features,
               created_at, updated_at
        FROM book_clubs ORDER BY created_at
    """, stats)
    data["book_clubs"] = [row_to_dict(r) for r in rows]

    # 2. book_club_members
    rows = await export_table(source, "book_club_members", """
        SELECT id, book_club_id, user_id, role, custom_title, rank_title,
               is_featured, invited_by, invite_code, joined_at
        FROM book_club_members ORDER BY joined_at
    """, stats)
    data["book_club_members"] = [row_to_dict(r) for r in rows]

    # 3. book_club_books
    rows = await export_table(source, "book_club_books", """
        SELECT id, book_club_id, book_id, shared_by, is_exclusive,
               deleted_at, deleted_by, shared_at
        FROM book_club_books ORDER BY shared_at
    """, stats)
    data["book_club_books"] = [row_to_dict(r) for r in rows]

    # 4. book_club_discussions
    rows = await export_table(source, "book_club_discussions", """
        SELECT id, club_id, book_id, author_id, title, content, tags,
               is_pinned, is_locked, likes_count, replies_count,
               created_at, updated_at
        FROM book_club_discussions ORDER BY created_at
    """, stats)
    data["book_club_discussions"] = [row_to_dict(r) for r in rows]

    # 5. book_club_discussion_replies
    rows = await export_table(source, "book_club_discussion_replies", """
        SELECT id, discussion_id, author_id, content, parent_reply_id,
               likes_count, created_at, updated_at
        FROM book_club_discussion_replies ORDER BY created_at
    """, stats)
    data["book_club_discussion_replies"] = [row_to_dict(r) for r in rows]

    # 6. book_club_invites
    rows = await export_table(source, "book_club_invites", """
        SELECT id, club_id, invite_code, title, created_by, max_uses,
               current_uses, is_active, expires_at, invite_url,
               created_at, updated_at
        FROM book_club_invites ORDER BY created_at
    """, stats)
    data["book_club_invites"] = [row_to_dict(r) for r in rows]

    # 7. book_club_activities
    rows = await export_table(source, "book_club_activities", """
        SELECT id, club_id, user_id, activity_type, activity_data,
               visibility, created_at
        FROM book_club_activities ORDER BY created_at
    """, stats)
    data["book_club_activities"] = [row_to_dict(r) for r in rows]

    # 8. book_club_challenges
    rows = await export_table(source, "book_club_challenges", """
        SELECT id, club_id, name, description, challenge_type, target_value,
               target_unit, reward_points, start_date, end_date, is_active,
               created_by, created_at, updated_at
        FROM book_club_challenges ORDER BY created_at
    """, stats)
    data["book_club_challenges"] = [row_to_dict(r) for r in rows]

    # 9. book_club_challenge_participants
    rows = await export_table(source, "book_club_challenge_participants", """
        SELECT id, challenge_id, member_id, current_progress, is_completed,
               completed_at, joined_at
        FROM book_club_challenge_participants ORDER BY joined_at
    """, stats)
    data["book_club_challenge_participants"] = [row_to_dict(r) for r in rows]

    # 10. book_club_nominations
    rows = await export_table(source, "book_club_nominations", """
        SELECT id, club_id, book_id, nominated_by, nomination_text,
               nomination_month, votes_count, status, created_at, updated_at
        FROM book_club_nominations ORDER BY created_at
    """, stats)
    data["book_club_nominations"] = [row_to_dict(r) for r in rows]

    # 11. book_club_votes
    rows = await export_table(source, "book_club_votes", """
        SELECT id, nomination_id, member_id, vote_weight, created_at
        FROM book_club_votes ORDER BY created_at
    """, stats)
    data["book_club_votes"] = [row_to_dict(r) for r in rows]

    # 12. book_club_notifications
    rows = await export_table(source, "book_club_notifications", """
        SELECT id, club_id, user_id, notification_type, title, content,
               data, is_read, created_at
        FROM book_club_notifications ORDER BY created_at
    """, stats)
    data["book_club_notifications"] = [row_to_dict(r) for r in rows]

    # 13. book_club_poster_history
    rows = await export_table(source, "book_club_poster_history", """
        SELECT id, book_club_id, cover_image_url, cover_image_path,
               cover_thumbnail_url, cover_thumbnail_path,
               file_size, image_width, image_height, is_current,
               version_notes, uploaded_by, uploaded_at, created_at
        FROM book_club_poster_history ORDER BY created_at
    """, stats)
    data["book_club_poster_history"] = [row_to_dict(r) for r in rows]

    # 14. book_club_exclusive_books
    rows = await export_table(source, "book_club_exclusive_books", """
        SELECT id, club_id, book_id, added_by, access_level,
               minimum_points, minimum_rank, created_at
        FROM book_club_exclusive_books ORDER BY created_at
    """, stats)
    data["book_club_exclusive_books"] = [row_to_dict(r) for r in rows]

    # 15. book_club_member_stats
    rows = await export_table(source, "book_club_member_stats", """
        SELECT id, book_club_id, member_id, books_read, books_shared,
               discussions_started, comments_posted, events_attended,
               total_points, monthly_points, monthly_books_read,
               reading_streak_days, last_activity_at,
               created_at, updated_at
        FROM book_club_member_stats ORDER BY created_at
    """, stats)
    data["book_club_member_stats"] = [row_to_dict(r) for r in rows]

    # 16. book_club_achievements
    rows = await export_table(source, "book_club_achievements", """
        SELECT id, name, description, icon, category, points_value,
               is_active, requirements, created_at, updated_at
        FROM book_club_achievements ORDER BY created_at
    """, stats)
    data["book_club_achievements"] = [row_to_dict(r) for r in rows]

    # 17. book_club_member_achievements
    rows = await export_table(source, "book_club_member_achievements", """
        SELECT id, achievement_id, member_id, club_id, earned_at
        FROM book_club_member_achievements ORDER BY earned_at
    """, stats)
    data["book_club_member_achievements"] = [row_to_dict(r) for r in rows]

    return data


# ---------------------------------------------------------------------------
# Import functions
# ---------------------------------------------------------------------------

async def import_book_clubs(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_clubs. Returns set of valid club IDs."""
    print("\nImporting book_clubs...")
    valid_club_ids: set[str] = set()

    for r in tqdm(rows, desc="  book_clubs"):
        owner_id = r["owner_id"]
        if owner_id not in valid_user_ids:
            stats.track("book_clubs", skipped=1)
            continue

        if dry_run:
            valid_club_ids.add(r["id"])
            stats.track("book_clubs", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_clubs (
                    id, name, description, tagline, summary, welcome_message,
                    cover_image_url, cover_thumbnail_url, owner_id,
                    visibility, club_type, max_members, member_limit,
                    is_premium_only, featured_book_id, settings, premium_features,
                    created_at, updated_at
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19
                )
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                r["name"],
                r.get("description"),
                r.get("tagline"),
                r.get("summary"),
                r.get("welcome_message"),
                r.get("cover_image_url"),
                r.get("cover_thumbnail_url"),
                UUID(owner_id),
                r.get("visibility", "public"),
                r.get("club_type"),
                r.get("max_members", 100),
                r.get("member_limit"),
                r.get("is_premium_only", False),
                safe_uuid(r.get("featured_book_id")),
                json.dumps(r.get("settings") or {}),
                json.dumps(r.get("premium_features") or {}),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_club_ids.add(r["id"])
            stats.track("book_clubs", imported=1)
        except Exception as e:
            stats.errors.append(f"book_clubs {r['id']}: {e}")
            stats.track("book_clubs", skipped=1)

    print(f"  Imported {stats.tables.get('book_clubs', {}).get('imported', 0)} clubs")
    return valid_club_ids


async def import_book_club_members(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_club_members. Returns set of valid member IDs."""
    print("\nImporting book_club_members...")
    valid_member_ids: set[str] = set()

    for r in tqdm(rows, desc="  book_club_members"):
        if r["book_club_id"] not in valid_club_ids:
            stats.track("book_club_members", skipped=1)
            continue
        if r["user_id"] not in valid_user_ids:
            stats.track("book_club_members", skipped=1)
            continue

        if dry_run:
            valid_member_ids.add(r["id"])
            stats.track("book_club_members", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_members (
                    id, book_club_id, user_id, role, custom_title, rank_title,
                    is_featured, invited_by, invite_code, joined_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["book_club_id"]),
                UUID(r["user_id"]),
                r.get("role", "member"),
                r.get("custom_title"),
                r.get("rank_title"),
                r.get("is_featured", False),
                safe_uuid(r.get("invited_by")),
                r.get("invite_code"),
                parse_dt(r.get("joined_at")) or datetime.now(UTC),
            )
            valid_member_ids.add(r["id"])
            stats.track("book_club_members", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_members {r['id']}: {e}")
            stats.track("book_club_members", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_members', {}).get('imported', 0)} members")
    return valid_member_ids


async def import_book_club_books(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_book_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_books."""
    print("\nImporting book_club_books...")

    for r in tqdm(rows, desc="  book_club_books"):
        if r["book_club_id"] not in valid_club_ids:
            stats.track("book_club_books", skipped=1)
            continue
        if r["book_id"] not in valid_book_ids:
            stats.track("book_club_books", skipped=1)
            continue

        shared_by = r.get("shared_by")
        if shared_by and shared_by not in valid_user_ids:
            shared_by = None

        if dry_run:
            stats.track("book_club_books", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_books (
                    id, book_club_id, book_id, shared_by, is_exclusive,
                    deleted_at, deleted_by, shared_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["book_club_id"]),
                UUID(r["book_id"]),
                safe_uuid(shared_by),
                r.get("is_exclusive", False),
                parse_dt(r.get("deleted_at")),
                safe_uuid(r.get("deleted_by")),
                parse_dt(r.get("shared_at")) or datetime.now(UTC),
            )
            stats.track("book_club_books", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_books {r['id']}: {e}")
            stats.track("book_club_books", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_books', {}).get('imported', 0)} club books")


async def import_book_club_discussions(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_book_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_club_discussions. Returns set of valid discussion IDs."""
    print("\nImporting book_club_discussions...")
    valid_discussion_ids: set[str] = set()

    for r in tqdm(rows, desc="  discussions"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_discussions", skipped=1)
            continue
        if r["author_id"] not in valid_user_ids:
            stats.track("book_club_discussions", skipped=1)
            continue

        book_id = r.get("book_id")
        if book_id and book_id not in valid_book_ids:
            book_id = None

        if dry_run:
            valid_discussion_ids.add(r["id"])
            stats.track("book_club_discussions", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_discussions (
                    id, club_id, book_id, author_id, title, content, tags,
                    is_pinned, is_locked, likes_count, replies_count,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                safe_uuid(book_id),
                UUID(r["author_id"]),
                r["title"],
                r["content"],
                r.get("tags") or [],
                r.get("is_pinned", False),
                r.get("is_locked", False),
                r.get("likes_count", 0),
                r.get("replies_count", 0),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_discussion_ids.add(r["id"])
            stats.track("book_club_discussions", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_discussions {r['id']}: {e}")
            stats.track("book_club_discussions", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_discussions', {}).get('imported', 0)} discussions")
    return valid_discussion_ids


async def import_book_club_discussion_replies(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_discussion_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_discussion_replies."""
    print("\nImporting book_club_discussion_replies...")

    for r in tqdm(rows, desc="  replies"):
        if r["discussion_id"] not in valid_discussion_ids:
            stats.track("book_club_discussion_replies", skipped=1)
            continue
        if r["author_id"] not in valid_user_ids:
            stats.track("book_club_discussion_replies", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_discussion_replies", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_discussion_replies (
                    id, discussion_id, author_id, content, parent_reply_id,
                    likes_count, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["discussion_id"]),
                UUID(r["author_id"]),
                r["content"],
                safe_uuid(r.get("parent_reply_id")),
                r.get("likes_count", 0),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            stats.track("book_club_discussion_replies", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_discussion_replies {r['id']}: {e}")
            stats.track("book_club_discussion_replies", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_discussion_replies', {}).get('imported', 0)} replies")


async def import_book_club_invites(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_invites."""
    print("\nImporting book_club_invites...")

    for r in tqdm(rows, desc="  invites"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_invites", skipped=1)
            continue
        if r["created_by"] not in valid_user_ids:
            stats.track("book_club_invites", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_invites", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_invites (
                    id, club_id, invite_code, title, created_by, max_uses,
                    current_uses, is_active, expires_at, invite_url,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                r["invite_code"],
                r.get("title"),
                UUID(r["created_by"]),
                r.get("max_uses"),
                r.get("current_uses", 0),
                r.get("is_active", True),
                parse_dt(r.get("expires_at")),
                r.get("invite_url"),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            stats.track("book_club_invites", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_invites {r['id']}: {e}")
            stats.track("book_club_invites", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_invites', {}).get('imported', 0)} invites")


async def import_book_club_activities(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_activities."""
    print("\nImporting book_club_activities...")

    for r in tqdm(rows, desc="  activities"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_activities", skipped=1)
            continue
        user_id = r.get("user_id")
        if user_id and user_id not in valid_user_ids:
            user_id = None

        if dry_run:
            stats.track("book_club_activities", imported=1)
            continue

        try:
            activity_data = r.get("activity_data")
            if isinstance(activity_data, str):
                activity_data = json.loads(activity_data)

            await target.execute(
                """
                INSERT INTO book_club_activities (
                    id, club_id, user_id, activity_type, activity_data,
                    visibility, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                safe_uuid(user_id),
                r["activity_type"],
                json.dumps(activity_data or {}),
                r.get("visibility", "members"),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("book_club_activities", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_activities {r['id']}: {e}")
            stats.track("book_club_activities", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_activities', {}).get('imported', 0)} activities")


async def import_book_club_challenges(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_club_challenges. Returns set of valid challenge IDs."""
    print("\nImporting book_club_challenges...")
    valid_challenge_ids: set[str] = set()

    for r in tqdm(rows, desc="  challenges"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_challenges", skipped=1)
            continue

        created_by = r.get("created_by")
        if created_by and created_by not in valid_user_ids:
            created_by = None

        if dry_run:
            valid_challenge_ids.add(r["id"])
            stats.track("book_club_challenges", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_challenges (
                    id, club_id, name, description, challenge_type, target_value,
                    target_unit, reward_points, start_date, end_date, is_active,
                    created_by, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                r["name"],
                r.get("description"),
                r.get("challenge_type", "reading"),
                r.get("target_value", 1),
                r.get("target_unit", "books"),
                r.get("reward_points", 0),
                parse_dt(r.get("start_date")),
                parse_dt(r.get("end_date")),
                r.get("is_active", True),
                safe_uuid(created_by),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_challenge_ids.add(r["id"])
            stats.track("book_club_challenges", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_challenges {r['id']}: {e}")
            stats.track("book_club_challenges", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_challenges', {}).get('imported', 0)} challenges")
    return valid_challenge_ids


async def import_book_club_challenge_participants(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_challenge_ids: set[str],
    valid_member_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_challenge_participants."""
    print("\nImporting book_club_challenge_participants...")

    for r in tqdm(rows, desc="  challenge participants"):
        if r["challenge_id"] not in valid_challenge_ids:
            stats.track("book_club_challenge_participants", skipped=1)
            continue
        if r["member_id"] not in valid_member_ids:
            stats.track("book_club_challenge_participants", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_challenge_participants", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_challenge_participants (
                    id, challenge_id, member_id, current_progress, is_completed,
                    completed_at, joined_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["challenge_id"]),
                UUID(r["member_id"]),
                r.get("current_progress", 0),
                r.get("is_completed", False),
                parse_dt(r.get("completed_at")),
                parse_dt(r.get("joined_at")) or datetime.now(UTC),
            )
            stats.track("book_club_challenge_participants", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_challenge_participants {r['id']}: {e}")
            stats.track("book_club_challenge_participants", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_challenge_participants', {}).get('imported', 0)} participants")


async def import_book_club_nominations(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_book_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_club_nominations. Returns set of valid nomination IDs."""
    print("\nImporting book_club_nominations...")
    valid_nomination_ids: set[str] = set()

    for r in tqdm(rows, desc="  nominations"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_nominations", skipped=1)
            continue
        if r["book_id"] not in valid_book_ids:
            stats.track("book_club_nominations", skipped=1)
            continue
        if r["nominated_by"] not in valid_user_ids:
            stats.track("book_club_nominations", skipped=1)
            continue

        if dry_run:
            valid_nomination_ids.add(r["id"])
            stats.track("book_club_nominations", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_nominations (
                    id, club_id, book_id, nominated_by, nomination_text,
                    nomination_month, votes_count, status, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                UUID(r["book_id"]),
                UUID(r["nominated_by"]),
                r.get("nomination_text"),
                r.get("nomination_month"),
                r.get("votes_count", 0),
                r.get("status", "pending"),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_nomination_ids.add(r["id"])
            stats.track("book_club_nominations", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_nominations {r['id']}: {e}")
            stats.track("book_club_nominations", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_nominations', {}).get('imported', 0)} nominations")
    return valid_nomination_ids


async def import_book_club_votes(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_nomination_ids: set[str],
    valid_member_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_votes."""
    print("\nImporting book_club_votes...")

    for r in tqdm(rows, desc="  votes"):
        if r["nomination_id"] not in valid_nomination_ids:
            stats.track("book_club_votes", skipped=1)
            continue
        if r["member_id"] not in valid_member_ids:
            stats.track("book_club_votes", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_votes", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_votes (
                    id, nomination_id, member_id, vote_weight, created_at
                ) VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["nomination_id"]),
                UUID(r["member_id"]),
                r.get("vote_weight", 1),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("book_club_votes", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_votes {r['id']}: {e}")
            stats.track("book_club_votes", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_votes', {}).get('imported', 0)} votes")


async def import_book_club_notifications(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_notifications."""
    print("\nImporting book_club_notifications...")

    for r in tqdm(rows, desc="  notifications"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_notifications", skipped=1)
            continue
        if r["user_id"] not in valid_user_ids:
            stats.track("book_club_notifications", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_notifications", imported=1)
            continue

        try:
            notif_data = r.get("data")
            if isinstance(notif_data, str):
                notif_data = json.loads(notif_data)

            await target.execute(
                """
                INSERT INTO book_club_notifications (
                    id, club_id, user_id, notification_type, title, content,
                    data, is_read, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                UUID(r["user_id"]),
                r["notification_type"],
                r["title"],
                r.get("content"),
                json.dumps(notif_data or {}),
                r.get("is_read", False),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("book_club_notifications", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_notifications {r['id']}: {e}")
            stats.track("book_club_notifications", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_notifications', {}).get('imported', 0)} notifications")


async def import_book_club_poster_history(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_poster_history."""
    print("\nImporting book_club_poster_history...")

    for r in tqdm(rows, desc="  poster history"):
        if r["book_club_id"] not in valid_club_ids:
            stats.track("book_club_poster_history", skipped=1)
            continue

        uploaded_by = r.get("uploaded_by")
        if uploaded_by and uploaded_by not in valid_user_ids:
            uploaded_by = None

        if dry_run:
            stats.track("book_club_poster_history", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_poster_history (
                    id, book_club_id, cover_image_url, cover_image_path,
                    cover_thumbnail_url, cover_thumbnail_path,
                    file_size, image_width, image_height, is_current,
                    version_notes, uploaded_by, uploaded_at, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["book_club_id"]),
                r.get("cover_image_url"),
                r.get("cover_image_path"),
                r.get("cover_thumbnail_url"),
                r.get("cover_thumbnail_path"),
                r.get("file_size"),
                r.get("image_width"),
                r.get("image_height"),
                r.get("is_current", False),
                r.get("version_notes"),
                safe_uuid(uploaded_by),
                parse_dt(r.get("uploaded_at")) or datetime.now(UTC),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("book_club_poster_history", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_poster_history {r['id']}: {e}")
            stats.track("book_club_poster_history", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_poster_history', {}).get('imported', 0)} poster entries")


async def import_book_club_exclusive_books(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_book_ids: set[str],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_exclusive_books."""
    print("\nImporting book_club_exclusive_books...")

    for r in tqdm(rows, desc="  exclusive books"):
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_exclusive_books", skipped=1)
            continue
        if r["book_id"] not in valid_book_ids:
            stats.track("book_club_exclusive_books", skipped=1)
            continue

        added_by = r.get("added_by")
        if added_by and added_by not in valid_user_ids:
            added_by = None

        if dry_run:
            stats.track("book_club_exclusive_books", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_exclusive_books (
                    id, club_id, book_id, added_by, access_level,
                    minimum_points, minimum_rank, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["club_id"]),
                UUID(r["book_id"]),
                safe_uuid(added_by),
                r.get("access_level", "members"),
                r.get("minimum_points", 0),
                r.get("minimum_rank"),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("book_club_exclusive_books", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_exclusive_books {r['id']}: {e}")
            stats.track("book_club_exclusive_books", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_exclusive_books', {}).get('imported', 0)} exclusive books")


async def import_book_club_member_stats(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_club_ids: set[str],
    valid_member_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_member_stats."""
    print("\nImporting book_club_member_stats...")

    for r in tqdm(rows, desc="  member stats"):
        if r["book_club_id"] not in valid_club_ids:
            stats.track("book_club_member_stats", skipped=1)
            continue
        if r["member_id"] not in valid_member_ids:
            stats.track("book_club_member_stats", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_member_stats", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_member_stats (
                    id, book_club_id, member_id, books_read, books_shared,
                    discussions_started, comments_posted, events_attended,
                    total_points, monthly_points, monthly_books_read,
                    reading_streak_days, last_activity_at,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                ON CONFLICT DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["book_club_id"]),
                UUID(r["member_id"]),
                r.get("books_read", 0),
                r.get("books_shared", 0),
                r.get("discussions_started", 0),
                r.get("comments_posted", 0),
                r.get("events_attended", 0),
                r.get("total_points", 0),
                r.get("monthly_points", 0),
                r.get("monthly_books_read", 0),
                r.get("reading_streak_days", 0),
                parse_dt(r.get("last_activity_at")),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            stats.track("book_club_member_stats", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_member_stats {r['id']}: {e}")
            stats.track("book_club_member_stats", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_member_stats', {}).get('imported', 0)} member stats")


async def import_book_club_achievements(
    target: asyncpg.Connection,
    rows: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import book_club_achievements. Returns valid achievement IDs."""
    print("\nImporting book_club_achievements...")
    valid_achievement_ids: set[str] = set()

    for r in tqdm(rows, desc="  achievements"):
        if dry_run:
            valid_achievement_ids.add(r["id"])
            stats.track("book_club_achievements", imported=1)
            continue

        try:
            requirements = r.get("requirements")
            if isinstance(requirements, str):
                requirements = json.loads(requirements)

            await target.execute(
                """
                INSERT INTO book_club_achievements (
                    id, name, description, icon, category, points_value,
                    is_active, requirements, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                r["name"],
                r.get("description"),
                r.get("icon"),
                r.get("category"),
                r.get("points_value", 0),
                r.get("is_active", True),
                json.dumps(requirements or {}),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_achievement_ids.add(r["id"])
            stats.track("book_club_achievements", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_achievements {r['id']}: {e}")
            stats.track("book_club_achievements", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_achievements', {}).get('imported', 0)} achievements")
    return valid_achievement_ids


async def import_book_club_member_achievements(
    target: asyncpg.Connection,
    rows: list[dict],
    valid_achievement_ids: set[str],
    valid_member_ids: set[str],
    valid_club_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import book_club_member_achievements."""
    print("\nImporting book_club_member_achievements...")

    for r in tqdm(rows, desc="  member achievements"):
        if r["achievement_id"] not in valid_achievement_ids:
            stats.track("book_club_member_achievements", skipped=1)
            continue
        if r["member_id"] not in valid_member_ids:
            stats.track("book_club_member_achievements", skipped=1)
            continue
        if r["club_id"] not in valid_club_ids:
            stats.track("book_club_member_achievements", skipped=1)
            continue

        if dry_run:
            stats.track("book_club_member_achievements", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO book_club_member_achievements (
                    id, achievement_id, member_id, club_id, earned_at
                ) VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["achievement_id"]),
                UUID(r["member_id"]),
                UUID(r["club_id"]),
                parse_dt(r.get("earned_at")) or datetime.now(UTC),
            )
            stats.track("book_club_member_achievements", imported=1)
        except Exception as e:
            stats.errors.append(f"book_club_member_achievements {r['id']}: {e}")
            stats.track("book_club_member_achievements", skipped=1)

    print(f"  Imported {stats.tables.get('book_club_member_achievements', {}).get('imported', 0)} member achievements")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(
    dry_run: bool = False,
    export_only: bool = False,
    skip_import: bool = False,
) -> int:
    """Main migration function."""
    print("\n" + "=" * 60)
    print("03 - MIGRATE BOOK CLUBS (17 tables)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXPORT ONLY' if export_only else 'SKIP IMPORT' if skip_import else 'FULL MIGRATION'}")
    print("=" * 60)

    stats = MigrationStats("03_migrate_clubs")

    # Connect to source
    source = await connect_source()

    try:
        # ---- Export ----
        data = await export_all(source, stats)

        # Save exports
        print("\nSaving exports...")
        save_export(data, "03_clubs_all")

        if export_only or skip_import:
            stats.print_summary()
            return 0

        # ---- Import ----
        target = await connect_target()

        try:
            # Load valid FK reference sets
            valid_user_ids = await get_valid_user_ids(target)
            valid_book_ids = await get_valid_book_ids(target)
            print(f"\n  Reference sets: {len(valid_user_ids)} users, {len(valid_book_ids)} books")

            # Import in FK order
            valid_club_ids = await import_book_clubs(
                target, data["book_clubs"], valid_user_ids, stats, dry_run
            )
            valid_member_ids = await import_book_club_members(
                target, data["book_club_members"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_books(
                target, data["book_club_books"], valid_club_ids, valid_book_ids, valid_user_ids, stats, dry_run
            )
            valid_discussion_ids = await import_book_club_discussions(
                target, data["book_club_discussions"], valid_club_ids, valid_book_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_discussion_replies(
                target, data["book_club_discussion_replies"], valid_discussion_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_invites(
                target, data["book_club_invites"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_activities(
                target, data["book_club_activities"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            valid_challenge_ids = await import_book_club_challenges(
                target, data["book_club_challenges"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_challenge_participants(
                target, data["book_club_challenge_participants"], valid_challenge_ids, valid_member_ids, stats, dry_run
            )
            valid_nomination_ids = await import_book_club_nominations(
                target, data["book_club_nominations"], valid_club_ids, valid_book_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_votes(
                target, data["book_club_votes"], valid_nomination_ids, valid_member_ids, stats, dry_run
            )
            await import_book_club_notifications(
                target, data["book_club_notifications"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_poster_history(
                target, data["book_club_poster_history"], valid_club_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_exclusive_books(
                target, data["book_club_exclusive_books"], valid_club_ids, valid_book_ids, valid_user_ids, stats, dry_run
            )
            await import_book_club_member_stats(
                target, data["book_club_member_stats"], valid_club_ids, valid_member_ids, stats, dry_run
            )
            valid_achievement_ids = await import_book_club_achievements(
                target, data["book_club_achievements"], stats, dry_run
            )
            await import_book_club_member_achievements(
                target, data["book_club_member_achievements"], valid_achievement_ids, valid_member_ids, valid_club_ids, stats, dry_run
            )

        finally:
            await target.close()

    finally:
        await source.close()

    stats.print_summary()
    return 0 if len(stats.errors) == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate book club data (17 tables) from Supabase to API PostgreSQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate import without writing to target",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only export data from Supabase, do not import",
    )
    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Export data and save to JSON, skip import step",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(
        main(
            dry_run=args.dry_run,
            export_only=args.export_only,
            skip_import=args.skip_import,
        )
    )
    sys.exit(exit_code)
