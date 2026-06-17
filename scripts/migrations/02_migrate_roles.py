#!/usr/bin/env python3
"""Migrate RBAC data (user_roles, role_assignment_logs) from Supabase to API PostgreSQL.

Supabase stores user_roles as an enum-based column (user_id, role text).
The API uses a junction table (user_roles) with user_id + role_id FK.

This script:
1. Verifies seed roles exist in target roles table
2. Exports user_roles from Supabase
3. Looks up role_id by name in target
4. Inserts into target user_roles junction table
5. Migrates role_assignment_logs if they exist

Usage:
    python scripts/migrations/02_migrate_roles.py
    python scripts/migrations/02_migrate_roles.py --dry-run
    python scripts/migrations/02_migrate_roles.py --export-only
    python scripts/migrations/02_migrate_roles.py --skip-import

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

# Mapping from Supabase role enum names to API role names.
# The API roles table is seeded by Alembic. Some Supabase names may differ.
ROLE_NAME_MAP = {
    "super_admin": "super_admin",
    "admin": "admin",
    "moderator": "moderator",
    "editor": "editor",
    "user": "user",
    "premium_user": "premium_user",
    "support": "support",
    "director_library_operations": "director_library_operations",
    "internal": "internal",
    "tester": "tester",
}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

async def export_user_roles(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export user_roles from Supabase."""
    print("\nExporting user_roles...")

    # Check if the table exists
    if not await table_exists(source, "user_roles"):
        print("  user_roles table not found in source, skipping")
        return []

    query = """
        SELECT user_id, role, created_at
        FROM user_roles
        ORDER BY created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    roles_data: list[dict] = []

    for row in tqdm(rows, desc="  User roles"):
        entry = {
            "user_id": str(row["user_id"]),
            "role": row["role"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") and row["created_at"] else None,
        }
        roles_data.append(entry)
        stats.track("user_roles", exported=1)

    print(f"  Exported {len(roles_data)} user role assignments")
    return roles_data


async def export_role_assignment_logs(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export role_assignment_logs from Supabase if the table exists."""
    print("\nExporting role_assignment_logs...")

    if not await table_exists(source, "role_assignment_logs"):
        print("  role_assignment_logs table not found in source, skipping")
        return []

    query = """
        SELECT id, user_id, role_id, action, performed_by, reason, metadata, created_at
        FROM role_assignment_logs
        ORDER BY created_at
    """

    try:
        rows = await fetch_paginated(source, query, BATCH_SIZE)
    except Exception:
        # Supabase may store role name instead of role_id; try alternate schema
        try:
            query = """
                SELECT id, user_id, role AS role_name, action, performed_by, reason, metadata, created_at
                FROM role_assignment_logs
                ORDER BY created_at
            """
            rows = await fetch_paginated(source, query, BATCH_SIZE)
        except Exception as e:
            print(f"  Cannot read role_assignment_logs: {e}")
            return []

    logs: list[dict] = []

    for row in tqdm(rows, desc="  Assignment logs"):
        log_entry = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "role_id": str(row["role_id"]) if "role_id" in row.keys() and row["role_id"] else None,
            "role_name": row.get("role_name"),
            "action": row["action"],
            "performed_by": str(row["performed_by"]) if row["performed_by"] else None,
            "reason": row.get("reason"),
            "metadata": json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else (row.get("metadata") or {}),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        logs.append(log_entry)
        stats.track("role_assignment_logs", exported=1)

    print(f"  Exported {len(logs)} role assignment logs")
    return logs


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

async def load_role_lookup(target: asyncpg.Connection) -> dict[str, str]:
    """Load roles from target and return name -> id mapping."""
    rows = await target.fetch("SELECT id, name FROM roles")
    lookup = {row["name"]: str(row["id"]) for row in rows}
    return lookup


async def import_user_roles(
    target: asyncpg.Connection,
    roles_data: list[dict],
    valid_user_ids: set[str],
    role_lookup: dict[str, str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import user role assignments to target user_roles junction table."""
    print("\nImporting user_roles...")

    for entry in tqdm(roles_data, desc="  User roles"):
        user_id = entry["user_id"]

        # Validate user exists
        if user_id not in valid_user_ids:
            stats.track("user_roles", skipped=1)
            continue

        # Map Supabase role name to API role name
        source_role = entry["role"]
        api_role_name = ROLE_NAME_MAP.get(source_role, source_role)

        # Look up role_id
        role_id = role_lookup.get(api_role_name)
        if not role_id:
            stats.errors.append(f"Role '{source_role}' (mapped to '{api_role_name}') not found in target roles table")
            stats.track("user_roles", skipped=1)
            continue

        if dry_run:
            stats.track("user_roles", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO user_roles (id, user_id, role_id, assigned_at)
                VALUES (gen_random_uuid(), $1, $2, $3)
                ON CONFLICT ON CONSTRAINT uq_user_role DO NOTHING
                """,
                UUID(user_id),
                UUID(role_id),
                parse_dt(entry.get("created_at")) or datetime.now(UTC),
            )
            stats.track("user_roles", imported=1)
        except Exception as e:
            stats.errors.append(f"UserRole user={user_id} role={api_role_name}: {e}")
            stats.track("user_roles", skipped=1)

    print(f"  Imported {stats.tables.get('user_roles', {}).get('imported', 0)} user role assignments")


async def import_role_assignment_logs(
    target: asyncpg.Connection,
    logs: list[dict],
    valid_user_ids: set[str],
    role_lookup: dict[str, str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import role assignment logs to target."""
    print("\nImporting role_assignment_logs...")

    if not logs:
        print("  No logs to import")
        return

    for log_entry in tqdm(logs, desc="  Assignment logs"):
        user_id = log_entry["user_id"]

        # Validate user exists
        if user_id not in valid_user_ids:
            stats.track("role_assignment_logs", skipped=1)
            continue

        # Resolve role_id: use existing role_id or look up by role_name
        role_id = log_entry.get("role_id")
        if not role_id and log_entry.get("role_name"):
            api_role_name = ROLE_NAME_MAP.get(log_entry["role_name"], log_entry["role_name"])
            role_id = role_lookup.get(api_role_name)

        if not role_id:
            stats.track("role_assignment_logs", skipped=1)
            continue

        # Validate performed_by if present
        performed_by = log_entry.get("performed_by")
        if performed_by and performed_by not in valid_user_ids:
            performed_by = None

        if dry_run:
            stats.track("role_assignment_logs", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO role_assignment_logs (
                    id, user_id, role_id, action, performed_by, reason, metadata, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT DO NOTHING
                """,
                UUID(log_entry["id"]),
                UUID(user_id),
                UUID(role_id),
                log_entry["action"],
                safe_uuid(performed_by),
                log_entry.get("reason"),
                json.dumps(log_entry.get("metadata") or {}),
                parse_dt(log_entry.get("created_at")) or datetime.now(UTC),
            )
            stats.track("role_assignment_logs", imported=1)
        except Exception as e:
            stats.errors.append(f"RoleAssignmentLog {log_entry['id']}: {e}")
            stats.track("role_assignment_logs", skipped=1)

    print(f"  Imported {stats.tables.get('role_assignment_logs', {}).get('imported', 0)} logs")


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
    print("02 - MIGRATE RBAC (Roles, User Roles, Assignment Logs)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXPORT ONLY' if export_only else 'SKIP IMPORT' if skip_import else 'FULL MIGRATION'}")
    print("=" * 60)

    stats = MigrationStats("02_migrate_roles")

    # Connect to source
    source = await connect_source()

    try:
        # ---- Export ----
        roles_data = await export_user_roles(source, stats)
        assignment_logs = await export_role_assignment_logs(source, stats)

        # Save exports
        print("\nSaving exports...")
        save_export({"user_roles": roles_data}, "02_user_roles")
        save_export({"role_assignment_logs": assignment_logs}, "02_role_assignment_logs")

        if export_only or skip_import:
            stats.print_summary()
            return 0

        # ---- Import ----
        target = await connect_target()

        try:
            # Verify seed roles exist
            role_lookup = await load_role_lookup(target)
            if not role_lookup:
                print("\n  ERROR: No roles found in target database!")
                print("  Please run Alembic seed migrations first (alembic upgrade head).")
                stats.errors.append("No roles found in target. Run seed migrations first.")
                stats.print_summary()
                return 1

            print(f"\n  Found {len(role_lookup)} roles in target: {', '.join(sorted(role_lookup.keys()))}")

            # Get valid user IDs
            valid_user_ids = await get_valid_user_ids(target)
            print(f"  Found {len(valid_user_ids)} valid users in target")

            # Import
            await import_user_roles(target, roles_data, valid_user_ids, role_lookup, stats, dry_run)
            await import_role_assignment_logs(target, assignment_logs, valid_user_ids, role_lookup, stats, dry_run)

        finally:
            await target.close()

    finally:
        await source.close()

    stats.print_summary()
    return 0 if len(stats.errors) == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate RBAC data (user_roles, assignment logs) from Supabase to API PostgreSQL"
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
