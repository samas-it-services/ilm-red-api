#!/usr/bin/env python3
"""Migrate users (enhanced profile) and OAuth accounts from Supabase to API PostgreSQL.

This script migrates:
- profiles -> users (with all Wave 6 extended profile columns)
- auth.identities -> oauth_accounts (for Google-authenticated users)

Usage:
    python scripts/migrations/01_migrate_users.py
    python scripts/migrations/01_migrate_users.py --dry-run
    python scripts/migrations/01_migrate_users.py --export-only
    python scripts/migrations/01_migrate_users.py --skip-import

Environment variables:
    SUPABASE_DB_URL: Supabase direct PostgreSQL connection string
    TARGET_DATABASE_URL: Target PostgreSQL URL
"""

import argparse
import asyncio
import json
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import asyncpg
from argon2 import PasswordHasher
from tqdm import tqdm

# Add parent to path so we can import _common
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.migrations._common import (
    BATCH_SIZE,
    MigrationStats,
    connect_source,
    connect_target,
    fetch_paginated,
    parse_dt,
    safe_uuid,
    save_export,
    table_exists,
)

ph = PasswordHasher()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

async def export_profiles(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export user profiles from Supabase profiles table with all extended columns."""
    print("\nExporting profiles...")

    query = """
        SELECT
            p.id,
            p.email,
            p.username,
            p.full_name,
            p.profile_picture_url,
            p.bio,
            p.is_premium_user,
            p.onboarding_completed,
            p.onboarding_completed_at,
            p.favorite_genres,
            p.reading_goal,
            p.language_preference,
            p.dark_mode,
            p.notifications_enabled,
            p.bookshelf_visibility,
            p.developer_mode,
            p.ai_chat_settings,
            p.total_points,
            p.location,
            p.date_of_birth,
            p.referral_source,
            p.referred_by,
            p.last_active_at,
            p.created_at,
            p.updated_at
        FROM profiles p
        WHERE p.email IS NOT NULL
        ORDER BY p.created_at
    """

    rows = await fetch_paginated(source, query, BATCH_SIZE)
    users: list[dict] = []

    for row in tqdm(rows, desc="  Profiles"):
        # Generate random password (users will use forgot-password or OAuth)
        random_password = secrets.token_urlsafe(32)
        password_hash = ph.hash(random_password)

        # Generate username from email if missing
        username = row["username"]
        if not username:
            email_prefix = row["email"].split("@")[0]
            username = f"{email_prefix}_{secrets.token_hex(3)}"

        display_name = row["full_name"] or username

        user = {
            "id": str(row["id"]),
            "email": row["email"],
            "username": username,
            "display_name": display_name,
            "full_name": row["full_name"],
            "avatar_url": row["profile_picture_url"],
            "profile_picture_url": row["profile_picture_url"],
            "bio": row["bio"],
            "password_hash": password_hash,
            "is_premium_user": row["is_premium_user"] or False,
            "onboarding_completed": row["onboarding_completed"] or False,
            "onboarding_completed_at": row["onboarding_completed_at"].isoformat() if row["onboarding_completed_at"] else None,
            "favorite_genres": row["favorite_genres"] or [],
            "reading_goal": row["reading_goal"],
            "language_preference": row["language_preference"] or ["en"],
            "dark_mode": row["dark_mode"] or False,
            "notifications_enabled": row["notifications_enabled"] if row["notifications_enabled"] is not None else True,
            "bookshelf_visibility": row["bookshelf_visibility"] or "public",
            "developer_mode": row["developer_mode"] or False,
            "ai_chat_settings": json.loads(row["ai_chat_settings"]) if isinstance(row["ai_chat_settings"], str) else (row["ai_chat_settings"] or {}),
            "total_points": row["total_points"] or 0,
            "location": row["location"],
            "date_of_birth": row["date_of_birth"].isoformat() if row["date_of_birth"] else None,
            "referral_source": row["referral_source"],
            "referred_by": str(row["referred_by"]) if row["referred_by"] else None,
            "last_active_at": row["last_active_at"].isoformat() if row["last_active_at"] else None,
            "roles": ["premium"] if row["is_premium_user"] else ["user"],
            "status": "active",
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
        users.append(user)
        stats.track("profiles", exported=1)

    print(f"  Exported {len(users)} profiles")
    return users


async def export_oauth_identities(source: asyncpg.Connection, stats: MigrationStats) -> list[dict]:
    """Export OAuth identities from Supabase auth.identities for Google-authenticated users."""
    print("\nExporting OAuth identities...")

    # Check if auth.identities table is accessible
    try:
        query = """
            SELECT
                i.id,
                i.user_id,
                i.provider,
                i.identity_data,
                i.created_at,
                i.updated_at
            FROM auth.identities i
            WHERE i.provider = 'google'
            ORDER BY i.created_at
        """
        rows = await fetch_paginated(source, query, BATCH_SIZE)
    except Exception as e:
        print(f"  Cannot access auth.identities: {e}")
        print("  Skipping OAuth identity export")
        return []

    identities: list[dict] = []

    for row in tqdm(rows, desc="  OAuth identities"):
        identity_data = row["identity_data"]
        if isinstance(identity_data, str):
            identity_data = json.loads(identity_data)

        # Extract provider_user_id from identity_data (Google sub)
        provider_user_id = identity_data.get("sub") or identity_data.get("provider_id") or str(row["id"])

        identity = {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "provider": row["provider"],
            "provider_user_id": provider_user_id,
            "identity_data": identity_data,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        identities.append(identity)
        stats.track("oauth_identities", exported=1)

    print(f"  Exported {len(identities)} OAuth identities")
    return identities


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

async def import_users(
    target: asyncpg.Connection,
    users: list[dict],
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Import users to target database with ON CONFLICT (id) DO UPDATE for profile merge."""
    print("\nImporting users...")

    valid_user_ids: set[str] = set()

    for user in tqdm(users, desc="  Users"):
        if dry_run:
            valid_user_ids.add(user["id"])
            stats.track("users", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO users (
                    id, email, username, display_name, full_name,
                    avatar_url, profile_picture_url, bio,
                    password_hash, roles, status, preferences,
                    is_premium_user, onboarding_completed, onboarding_completed_at,
                    favorite_genres, reading_goal, language_preference,
                    dark_mode, notifications_enabled, bookshelf_visibility,
                    developer_mode, ai_chat_settings, total_points,
                    location, date_of_birth,
                    referral_source, referred_by, last_active_at,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8,
                    $9, $10, $11, $12,
                    $13, $14, $15,
                    $16, $17, $18,
                    $19, $20, $21,
                    $22, $23, $24,
                    $25, $26,
                    $27, $28, $29,
                    $30, $31
                )
                ON CONFLICT (id) DO UPDATE SET
                    display_name = COALESCE(EXCLUDED.display_name, users.display_name),
                    full_name = COALESCE(EXCLUDED.full_name, users.full_name),
                    avatar_url = COALESCE(EXCLUDED.avatar_url, users.avatar_url),
                    profile_picture_url = COALESCE(EXCLUDED.profile_picture_url, users.profile_picture_url),
                    bio = COALESCE(EXCLUDED.bio, users.bio),
                    is_premium_user = EXCLUDED.is_premium_user,
                    onboarding_completed = EXCLUDED.onboarding_completed,
                    onboarding_completed_at = COALESCE(EXCLUDED.onboarding_completed_at, users.onboarding_completed_at),
                    favorite_genres = EXCLUDED.favorite_genres,
                    reading_goal = COALESCE(EXCLUDED.reading_goal, users.reading_goal),
                    language_preference = EXCLUDED.language_preference,
                    dark_mode = EXCLUDED.dark_mode,
                    notifications_enabled = EXCLUDED.notifications_enabled,
                    bookshelf_visibility = EXCLUDED.bookshelf_visibility,
                    developer_mode = EXCLUDED.developer_mode,
                    ai_chat_settings = EXCLUDED.ai_chat_settings,
                    total_points = EXCLUDED.total_points,
                    location = COALESCE(EXCLUDED.location, users.location),
                    date_of_birth = COALESCE(EXCLUDED.date_of_birth, users.date_of_birth),
                    referral_source = COALESCE(EXCLUDED.referral_source, users.referral_source),
                    referred_by = COALESCE(EXCLUDED.referred_by, users.referred_by),
                    last_active_at = GREATEST(EXCLUDED.last_active_at, users.last_active_at),
                    updated_at = EXCLUDED.updated_at
                """,
                UUID(user["id"]),
                user["email"],
                user["username"],
                user["display_name"],
                user.get("full_name"),
                user.get("avatar_url"),
                user.get("profile_picture_url"),
                user.get("bio"),
                user["password_hash"],
                user["roles"],
                user["status"],
                json.dumps({}),
                user.get("is_premium_user", False),
                user.get("onboarding_completed", False),
                parse_dt(user.get("onboarding_completed_at")),
                user.get("favorite_genres") or [],
                user.get("reading_goal"),
                user.get("language_preference") or ["en"],
                user.get("dark_mode", False),
                user.get("notifications_enabled", True),
                user.get("bookshelf_visibility", "public"),
                user.get("developer_mode", False),
                json.dumps(user.get("ai_chat_settings") or {}),
                user.get("total_points", 0),
                user.get("location"),
                parse_dt(user.get("date_of_birth")).date() if parse_dt(user.get("date_of_birth")) else None,
                user.get("referral_source"),
                safe_uuid(user.get("referred_by")),
                parse_dt(user.get("last_active_at")),
                parse_dt(user.get("created_at")) or datetime.now(UTC),
                parse_dt(user.get("updated_at")) or datetime.now(UTC),
            )
            valid_user_ids.add(user["id"])
            stats.track("users", imported=1)
        except Exception as e:
            stats.errors.append(f"User {user['email']}: {e}")
            stats.track("users", skipped=1)

    print(f"  Imported {stats.tables.get('users', {}).get('imported', 0)} users")
    return valid_user_ids


async def import_oauth_accounts(
    target: asyncpg.Connection,
    identities: list[dict],
    valid_user_ids: set[str],
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Import OAuth accounts to target oauth_accounts table."""
    print("\nImporting OAuth accounts...")

    for identity in tqdm(identities, desc="  OAuth accounts"):
        user_id = identity["user_id"]

        # Skip if user doesn't exist in target
        if user_id not in valid_user_ids:
            stats.track("oauth_accounts", skipped=1)
            continue

        if dry_run:
            stats.track("oauth_accounts", imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO oauth_accounts (
                    id, user_id, provider, provider_user_id,
                    access_token, refresh_token, expires_at,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT DO NOTHING
                """,
                UUID(identity["id"]),
                UUID(user_id),
                identity["provider"],
                identity["provider_user_id"],
                None,  # access_token - not migrated for security
                None,  # refresh_token - not migrated for security
                None,  # expires_at
                parse_dt(identity.get("created_at")) or datetime.now(UTC),
            )
            stats.track("oauth_accounts", imported=1)
        except Exception as e:
            stats.errors.append(f"OAuth {identity['provider']} for user {user_id}: {e}")
            stats.track("oauth_accounts", skipped=1)

    print(f"  Imported {stats.tables.get('oauth_accounts', {}).get('imported', 0)} OAuth accounts")


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
    print("01 - MIGRATE USERS (Enhanced Profiles + OAuth)")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXPORT ONLY' if export_only else 'SKIP IMPORT' if skip_import else 'FULL MIGRATION'}")
    print("=" * 60)

    stats = MigrationStats("01_migrate_users")

    # Connect to source
    source = await connect_source()

    try:
        # ---- Export ----
        users = await export_profiles(source, stats)
        identities = await export_oauth_identities(source, stats)

        # Save exports
        print("\nSaving exports...")
        save_export({"users": users}, "01_users")
        save_export({"oauth_identities": identities}, "01_oauth_identities")

        if export_only or skip_import:
            stats.print_summary()
            return 0

        # ---- Import ----
        target = await connect_target()

        try:
            valid_user_ids = await import_users(target, users, stats, dry_run)
            await import_oauth_accounts(target, identities, valid_user_ids, stats, dry_run)
        finally:
            await target.close()

    finally:
        await source.close()

    stats.print_summary()
    return 0 if len(stats.errors) == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate users (enhanced profiles + OAuth) from Supabase to API PostgreSQL"
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
