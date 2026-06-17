#!/usr/bin/env python3
"""Migrate gamification data from Supabase to API PostgreSQL.

Tables migrated:
1. gamification_activities  (activity definitions)
2. badges                   (badge definitions)
3. ranks                    (rank definitions)
4. points_history           (user point ledger)
5. user_activity_log        (user activity events)
6. user_badges              (badges earned by users)
7. user_ranks               (user rank assignments)

Definitions are imported with ON CONFLICT DO UPDATE (seed data may differ).
User data is imported with ON CONFLICT DO NOTHING (idempotent).

Usage:
    python scripts/migrations/04_migrate_gamification.py
    python scripts/migrations/04_migrate_gamification.py --dry-run
    python scripts/migrations/04_migrate_gamification.py --export-only
    python scripts/migrations/04_migrate_gamification.py --skip-import

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
    get_valid_user_ids,
    parse_dt,
    safe_uuid,
    save_export,
    table_exists,
)


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

async def export_gamification_activities(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export gamification_activities definitions."""
    print("\nExporting gamification_activities...")

    if not await table_exists(source, "gamification_activities"):
        print("  gamification_activities table not found, skipping")
        return []

    query = """
        SELECT id, name, display_name, description, points,
               cooldown_hours, max_daily_occurrences, is_active,
               created_at, updated_at
        FROM gamification_activities
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  Activities"):
        items.append({
            "id": str(row["id"]),
            "name": row["name"],
            "display_name": row["display_name"],
            "description": row.get("description"),
            "points": row["points"],
            "cooldown_hours": row.get("cooldown_hours", 0),
            "max_daily_occurrences": row.get("max_daily_occurrences", 100),
            "is_active": row.get("is_active", True),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") and row["updated_at"] else None,
        })
        stats.track("gamification_activities", exported=1)

    print(f"  Exported {len(items)} activity definitions")
    return items


async def export_badges(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export badge definitions."""
    print("\nExporting badges...")

    if not await table_exists(source, "badges"):
        print("  badges table not found, skipping")
        return []

    query = """
        SELECT id, name, display_name, description, category,
               icon, color, rarity, points_awarded, is_active,
               created_at, updated_at
        FROM badges
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  Badges"):
        items.append({
            "id": str(row["id"]),
            "name": row["name"],
            "display_name": row["display_name"],
            "description": row.get("description"),
            "category": row.get("category", "achievement"),
            "icon": row.get("icon"),
            "color": row.get("color"),
            "rarity": row.get("rarity", "common"),
            "points_awarded": row.get("points_awarded", 0),
            "is_active": row.get("is_active", True),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") and row["updated_at"] else None,
        })
        stats.track("badges", exported=1)

    print(f"  Exported {len(items)} badge definitions")
    return items


async def export_ranks(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export rank definitions."""
    print("\nExporting ranks...")

    if not await table_exists(source, "ranks"):
        print("  ranks table not found, skipping")
        return []

    query = """
        SELECT id, name, display_name, description, level, min_points,
               color, icon, benefits, created_at, updated_at
        FROM ranks
        ORDER BY level
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  Ranks"):
        items.append({
            "id": str(row["id"]),
            "name": row["name"],
            "display_name": row["display_name"],
            "description": row.get("description"),
            "level": row["level"],
            "min_points": row["min_points"],
            "color": row.get("color"),
            "icon": row.get("icon"),
            "benefits": row.get("benefits") or [],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") and row["updated_at"] else None,
        })
        stats.track("ranks", exported=1)

    print(f"  Exported {len(items)} rank definitions")
    return items


async def export_points_history(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export points_history ledger."""
    print("\nExporting points_history...")

    if not await table_exists(source, "points_history"):
        print("  points_history table not found, skipping")
        return []

    query = """
        SELECT id, user_id, source, source_id, points, reason,
               metadata, created_at
        FROM points_history
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  Points history"):
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        items.append({
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "source": row["source"],
            "source_id": str(row["source_id"]) if row.get("source_id") else None,
            "points": row["points"],
            "reason": row.get("reason"),
            "metadata": metadata or {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
        stats.track("points_history", exported=1)

    print(f"  Exported {len(items)} points history entries")
    return items


async def export_user_activity_log(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export user_activity_log."""
    print("\nExporting user_activity_log...")

    if not await table_exists(source, "user_activity_log"):
        print("  user_activity_log table not found, skipping")
        return []

    query = """
        SELECT id, user_id, activity_id, points_earned, metadata, created_at
        FROM user_activity_log
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  Activity log"):
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        items.append({
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "activity_id": str(row["activity_id"]),
            "points_earned": row.get("points_earned", 0),
            "metadata": metadata or {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
        stats.track("user_activity_log", exported=1)

    print(f"  Exported {len(items)} activity log entries")
    return items


async def export_user_badges(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export user_badges."""
    print("\nExporting user_badges...")

    if not await table_exists(source, "user_badges"):
        print("  user_badges table not found, skipping")
        return []

    query = """
        SELECT id, user_id, badge_id, awarded_by, metadata, earned_at
        FROM user_badges
        ORDER BY earned_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  User badges"):
        metadata = row.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        items.append({
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "badge_id": str(row["badge_id"]),
            "awarded_by": str(row["awarded_by"]) if row.get("awarded_by") else None,
            "metadata": metadata or {},
            "earned_at": row["earned_at"].isoformat() if row["earned_at"] else None,
        })
        stats.track("user_badges", exported=1)

    print(f"  Exported {len(items)} user badge awards")
    return items


async def export_user_ranks(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export user_ranks."""
    print("\nExporting user_ranks...")

    if not await table_exists(source, "user_ranks"):
        print("  user_ranks table not found, skipping")
        return []

    query = """
        SELECT id, user_id, rank_id, current_points, total_points_earned,
               rank_achieved_at, assigned_by, created_at, updated_at
        FROM user_ranks
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    items: list[dict] = []

    for row in tqdm(rows, desc="  User ranks"):
        items.append({
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "rank_id": str(row["rank_id"]),
            "current_points": row.get("current_points", 0),
            "total_points_earned": row.get("total_points_earned", 0),
            "rank_achieved_at": row["rank_achieved_at"].isoformat() if row.get("rank_achieved_at") else None,
            "assigned_by": str(row["assigned_by"]) if row.get("assigned_by") else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") and row["updated_at"] else None,
        })
        stats.track("user_ranks", exported=1)

    print(f"  Exported {len(items)} user rank entries")
    return items


# ---------------------------------------------------------------------------
# Import functions
# ---------------------------------------------------------------------------

async def import_gamification_activities(
    target: asyncpg.Connection,
    items: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import gamification_activities with ON CONFLICT DO UPDATE."""
    print("\nImporting gamification_activities...")
    valid_activity_ids: set[str] = set()

    for r in tqdm(items, desc="  Activities"):
        if dry_run:
            valid_activity_ids.add(r["id"])
            stats.track("gamification_activities", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO gamification_activities (
                    id, name, display_name, description, points,
                    cooldown_hours, max_daily_occurrences, is_active,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    points = EXCLUDED.points,
                    cooldown_hours = EXCLUDED.cooldown_hours,
                    max_daily_occurrences = EXCLUDED.max_daily_occurrences,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(r["id"]),
                r["name"],
                r["display_name"],
                r.get("description"),
                r["points"],
                r.get("cooldown_hours", 0),
                r.get("max_daily_occurrences", 100),
                r.get("is_active", True),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_activity_ids.add(r["id"])
            stats.track("gamification_activities", imported=1)
        except Exception as e:
            stats.errors.append(f"gamification_activities {r['name']}: {e}")
            stats.track("gamification_activities", skipped=1)

    # Also load any pre-existing activities from target
    existing = await target.fetch("SELECT id FROM gamification_activities")
    for row in existing:
        valid_activity_ids.add(str(row["id"]))

    print(f"  Imported {stats.tables.get('gamification_activities', {}).get('imported', 0)} activity definitions")
    return valid_activity_ids


async def import_badges(
    target: asyncpg.Connection,
    items: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import badges with ON CONFLICT DO UPDATE."""
    print("\nImporting badges...")
    valid_badge_ids: set[str] = set()

    for r in tqdm(items, desc="  Badges"):
        if dry_run:
            valid_badge_ids.add(r["id"])
            stats.track("badges", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO badges (
                    id, name, display_name, description, category,
                    icon, color, rarity, points_awarded, is_active,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    icon = EXCLUDED.icon,
                    color = EXCLUDED.color,
                    rarity = EXCLUDED.rarity,
                    points_awarded = EXCLUDED.points_awarded,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(r["id"]),
                r["name"],
                r["display_name"],
                r.get("description"),
                r.get("category", "achievement"),
                r.get("icon"),
                r.get("color"),
                r.get("rarity", "common"),
                r.get("points_awarded", 0),
                r.get("is_active", True),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_badge_ids.add(r["id"])
            stats.track("badges", imported=1)
        except Exception as e:
            stats.errors.append(f"badges {r['name']}: {e}")
            stats.track("badges", skipped=1)

    # Also load any pre-existing badges from target
    existing = await target.fetch("SELECT id FROM badges")
    for row in existing:
        valid_badge_ids.add(str(row["id"]))

    print(f"  Imported {stats.tables.get('badges', {}).get('imported', 0)} badge definitions")
    return valid_badge_ids


async def import_ranks(
    target: asyncpg.Connection,
    items: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import ranks with ON CONFLICT DO UPDATE."""
    print("\nImporting ranks...")
    valid_rank_ids: set[str] = set()

    for r in tqdm(items, desc="  Ranks"):
        if dry_run:
            valid_rank_ids.add(r["id"])
            stats.track("ranks", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO ranks (
                    id, name, display_name, description, level, min_points,
                    color, icon, benefits, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (name) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    level = EXCLUDED.level,
                    min_points = EXCLUDED.min_points,
                    color = EXCLUDED.color,
                    icon = EXCLUDED.icon,
                    benefits = EXCLUDED.benefits,
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(r["id"]),
                r["name"],
                r["display_name"],
                r.get("description"),
                r["level"],
                r["min_points"],
                r.get("color"),
                r.get("icon"),
                r.get("benefits") or [],
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            valid_rank_ids.add(r["id"])
            stats.track("ranks", imported=1)
        except Exception as e:
            stats.errors.append(f"ranks {r['name']}: {e}")
            stats.track("ranks", skipped=1)

    # Also load any pre-existing ranks from target
    existing = await target.fetch("SELECT id FROM ranks")
    for row in existing:
        valid_rank_ids.add(str(row["id"]))

    print(f"  Imported {stats.tables.get('ranks', {}).get('imported', 0)} rank definitions")
    return valid_rank_ids


async def import_points_history(
    target: asyncpg.Connection,
    items: list[dict],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import points_history with ON CONFLICT DO NOTHING."""
    print("\nImporting points_history...")

    for r in tqdm(items, desc="  Points history"):
        if r["user_id"] not in valid_user_ids:
            stats.track("points_history", skipped=1)
            continue

        if dry_run:
            stats.track("points_history", imported=1)
            continue

        try:
            metadata = r.get("metadata")
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            await target.execute(
                """
                INSERT INTO points_history (
                    id, user_id, source, source_id, points, reason,
                    metadata, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["user_id"]),
                r["source"],
                safe_uuid(r.get("source_id")),
                r["points"],
                r.get("reason"),
                json.dumps(metadata or {}),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("points_history", imported=1)
        except Exception as e:
            stats.errors.append(f"points_history {r['id']}: {e}")
            stats.track("points_history", skipped=1)

    print(f"  Imported {stats.tables.get('points_history', {}).get('imported', 0)} points entries")


async def import_user_activity_log(
    target: asyncpg.Connection,
    items: list[dict],
    valid_user_ids: set[str],
    valid_activity_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import user_activity_log with ON CONFLICT DO NOTHING."""
    print("\nImporting user_activity_log...")

    for r in tqdm(items, desc="  Activity log"):
        if r["user_id"] not in valid_user_ids:
            stats.track("user_activity_log", skipped=1)
            continue
        if r["activity_id"] not in valid_activity_ids:
            stats.track("user_activity_log", skipped=1)
            continue

        if dry_run:
            stats.track("user_activity_log", imported=1)
            continue

        try:
            metadata = r.get("metadata")
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            await target.execute(
                """
                INSERT INTO user_activity_log (
                    id, user_id, activity_id, points_earned, metadata, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT (id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["user_id"]),
                UUID(r["activity_id"]),
                r.get("points_earned", 0),
                json.dumps(metadata or {}),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
            )
            stats.track("user_activity_log", imported=1)
        except Exception as e:
            stats.errors.append(f"user_activity_log {r['id']}: {e}")
            stats.track("user_activity_log", skipped=1)

    print(f"  Imported {stats.tables.get('user_activity_log', {}).get('imported', 0)} activity log entries")


async def import_user_badges(
    target: asyncpg.Connection,
    items: list[dict],
    valid_user_ids: set[str],
    valid_badge_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import user_badges with ON CONFLICT DO NOTHING."""
    print("\nImporting user_badges...")

    for r in tqdm(items, desc="  User badges"):
        if r["user_id"] not in valid_user_ids:
            stats.track("user_badges", skipped=1)
            continue
        if r["badge_id"] not in valid_badge_ids:
            stats.track("user_badges", skipped=1)
            continue

        awarded_by = r.get("awarded_by")
        if awarded_by and awarded_by not in valid_user_ids:
            awarded_by = None

        if dry_run:
            stats.track("user_badges", imported=1)
            continue

        try:
            metadata = r.get("metadata")
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            await target.execute(
                """
                INSERT INTO user_badges (
                    id, user_id, badge_id, awarded_by, metadata, earned_at
                ) VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT ON CONSTRAINT uq_user_badge DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["user_id"]),
                UUID(r["badge_id"]),
                safe_uuid(awarded_by),
                json.dumps(metadata or {}),
                parse_dt(r.get("earned_at")) or datetime.now(UTC),
            )
            stats.track("user_badges", imported=1)
        except Exception as e:
            stats.errors.append(f"user_badges {r['id']}: {e}")
            stats.track("user_badges", skipped=1)

    print(f"  Imported {stats.tables.get('user_badges', {}).get('imported', 0)} user badges")


async def import_user_ranks(
    target: asyncpg.Connection,
    items: list[dict],
    valid_user_ids: set[str],
    valid_rank_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import user_ranks with ON CONFLICT DO NOTHING (unique on user_id)."""
    print("\nImporting user_ranks...")

    for r in tqdm(items, desc="  User ranks"):
        if r["user_id"] not in valid_user_ids:
            stats.track("user_ranks", skipped=1)
            continue
        if r["rank_id"] not in valid_rank_ids:
            stats.track("user_ranks", skipped=1)
            continue

        assigned_by = r.get("assigned_by")
        if assigned_by and assigned_by not in valid_user_ids:
            assigned_by = None

        if dry_run:
            stats.track("user_ranks", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO user_ranks (
                    id, user_id, rank_id, current_points, total_points_earned,
                    rank_achieved_at, assigned_by, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                ON CONFLICT (user_id) DO NOTHING
                """,
                UUID(r["id"]),
                UUID(r["user_id"]),
                UUID(r["rank_id"]),
                r.get("current_points", 0),
                r.get("total_points_earned", 0),
                parse_dt(r.get("rank_achieved_at")),
                safe_uuid(assigned_by),
                parse_dt(r.get("created_at")) or datetime.now(UTC),
                parse_dt(r.get("updated_at")) or datetime.now(UTC),
            )
            stats.track("user_ranks", imported=1)
        except Exception as e:
            stats.errors.append(f"user_ranks {r['id']}: {e}")
            stats.track("user_ranks", skipped=1)

    print(f"  Imported {stats.tables.get('user_ranks', {}).get('imported', 0)} user ranks")


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
    print("04 - MIGRATE GAMIFICATION (7 tables)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXPORT ONLY' if export_only else 'SKIP IMPORT' if skip_import else 'FULL MIGRATION'}")
    print("=" * 60)

    stats = MigrationStats("04_migrate_gamification")

    # Connect to source
    source = await connect_source()

    try:
        # ---- Export ----
        activities = await export_gamification_activities(source, stats)
        badges = await export_badges(source, stats)
        ranks = await export_ranks(source, stats)
        points_history = await export_points_history(source, stats)
        activity_log = await export_user_activity_log(source, stats)
        user_badges = await export_user_badges(source, stats)
        user_ranks = await export_user_ranks(source, stats)

        # Save exports
        print("\nSaving exports...")
        save_export({
            "gamification_activities": activities,
            "badges": badges,
            "ranks": ranks,
            "points_history": points_history,
            "user_activity_log": activity_log,
            "user_badges": user_badges,
            "user_ranks": user_ranks,
        }, "04_gamification_all")

        if export_only or skip_import:
            stats.print_summary()
            return 0

        # ---- Import ----
        target = await connect_target()

        try:
            # Load valid user IDs
            valid_user_ids = await get_valid_user_ids(target)
            print(f"\n  Reference set: {len(valid_user_ids)} valid users")

            # 1. Import definitions (ON CONFLICT DO UPDATE)
            valid_activity_ids = await import_gamification_activities(target, activities, stats, dry_run)
            valid_badge_ids = await import_badges(target, badges, stats, dry_run)
            valid_rank_ids = await import_ranks(target, ranks, stats, dry_run)

            # 2. Import user data (ON CONFLICT DO NOTHING)
            await import_points_history(target, points_history, valid_user_ids, stats, dry_run)
            await import_user_activity_log(target, activity_log, valid_user_ids, valid_activity_ids, stats, dry_run)
            await import_user_badges(target, user_badges, valid_user_ids, valid_badge_ids, stats, dry_run)
            await import_user_ranks(target, user_ranks, valid_user_ids, valid_rank_ids, stats, dry_run)

        finally:
            await target.close()

    finally:
        await source.close()

    stats.print_summary()
    return 0 if len(stats.errors) == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate gamification data (7 tables) from Supabase to API PostgreSQL"
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
