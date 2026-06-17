#!/usr/bin/env python3
"""Migrate miscellaneous data from Supabase to API PostgreSQL.

Tables migrated (grouped):
  Issues (2):          user_issues, user_issue_responses
  Error Logs (1):      error_logs
  Addons (10):         addon_registry, addon_permissions, addon_tabs,
                       addon_storage, addon_error_logs, addon_usage_analytics,
                       addon_reviews, global_addon_config,
                       book_club_addon_config, default_addon_seeds
  Premium (5):         premium_features, premium_requests,
                       user_premium_subscriptions, stripe_payment_intents,
                       user_upload_limits
  Public QA (5):       public_qa, public_qa_edit_history, public_qa_feedback,
                       public_qa_views, public_qa_votes
  Suggestions (6):     user_suggestions, suggestion_config,
                       suggestion_system_config, suggestion_feedback,
                       suggestion_notifications, user_suggestion_usage
  Rankings (4):        ranking_contexts, ranking_settings,
                       user_context_rankings, context_points_history
  Admin Settings (2):  admin_settings, mystical_messages
  Copyright (1):       book_discovery_rewards
  Expert (3):          expert_configurations, session_participants,
                       session_analytics
  Search Analytics (1): search_analytics
  Billing (4):         ai_billing_config, user_ai_billing,
                       ai_usage_records, monthly_billing_summaries
  Book Club AI (6):    book_club_ai_credits, book_club_ai_credit_transactions,
                       book_club_ai_models, book_club_ai_chat_sessions,
                       book_club_ai_chat_messages, book_club_ai_chat_participants

Usage:
    python scripts/migrations/07_migrate_misc.py
    python scripts/migrations/07_migrate_misc.py --dry-run
    python scripts/migrations/07_migrate_misc.py --export-only

Environment variables:
    SUPABASE_DB_URL: Supabase PostgreSQL connection URL
    TARGET_DATABASE_URL: Target PostgreSQL connection URL
"""

import argparse
import asyncio
import json
import sys
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


# ========================================================================
# Generic migration helper
# ========================================================================


async def migrate_generic(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    table: str,
    *,
    order_by: str = "id",
    fk_checks: dict[str, set[str]] | None = None,
    nullable_fks: set[str] | None = None,
    dry_run: bool = False,
) -> set[str]:
    """Generic table migration with optional FK validation.

    Args:
        source: Source database connection.
        target: Target database connection.
        stats: Migration stats tracker.
        table: Table name (same in source and target).
        order_by: Column(s) to ORDER BY.
        fk_checks: Mapping of column_name -> set of valid IDs for FK validation.
                    Records with invalid FKs are skipped.
        nullable_fks: Set of FK column names that are allowed to be NULL.
                      If a nullable FK is NULL, the record is still migrated.
        dry_run: If True, don't write to target.

    Returns:
        Set of migrated row IDs (stringified).
    """
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    if target and not await table_exists(target, table):
        print(f"  Target table {table} does not exist - skipping")
        return set()

    fk_checks = fk_checks or {}
    nullable_fks = nullable_fks or set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY {order_by}")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        # Determine row id for tracking
        row_id = str(row["id"]) if "id" in row.keys() else None

        # FK validation
        skip = False
        for fk_col, valid_set in fk_checks.items():
            fk_val = row.get(fk_col)
            if fk_val is None:
                if fk_col not in nullable_fks:
                    skip = True
                    break
                # Nullable FK with NULL value is fine
                continue
            if str(fk_val) not in valid_set:
                skip = True
                break

        if skip:
            stats.track(table, skipped=1)
            continue

        if row_id:
            valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            cols = list(row.keys())
            placeholders = [f"${i+1}" for i in range(len(cols))]
            values = []
            for col in cols:
                val = row[col]
                if val is None:
                    values.append(None)
                elif col.endswith("_id") or col == "id":
                    values.append(safe_uuid(val))
                elif col.endswith("_at") or col in ("start_date", "end_date", "viewed_at", "dismissed_at"):
                    values.append(parse_dt(val))
                elif isinstance(val, dict):
                    values.append(json.dumps(val))
                elif isinstance(val, list) and val and isinstance(val[0], dict):
                    values.append(json.dumps(val))
                else:
                    values.append(val)

            col_str = ", ".join(cols)
            ph_str = ", ".join(placeholders)

            # Use ON CONFLICT DO NOTHING - requires id or PK
            conflict_clause = "ON CONFLICT DO NOTHING"
            if "id" in cols:
                conflict_clause = "ON CONFLICT (id) DO NOTHING"

            await target.execute(
                f"INSERT INTO {table} ({col_str}) VALUES ({ph_str}) {conflict_clause}",
                *values,
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables.get(table, {})}")
    return valid_ids


# ========================================================================
# Group migration functions
# ========================================================================


async def migrate_issues(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate user_issues and user_issue_responses."""
    print("\n--- Issues ---")

    issue_ids = await migrate_generic(
        source, target, stats, "user_issues",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    await migrate_generic(
        source, target, stats, "user_issue_responses",
        fk_checks={"issue_id": issue_ids, "responder_id": valid_user_ids},
        nullable_fks={"responder_id"},
        dry_run=dry_run,
    )


async def migrate_error_logs(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate error_logs."""
    print("\n--- Error Logs ---")

    await migrate_generic(
        source, target, stats, "error_logs",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )


async def migrate_addons(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate addon tables in FK order."""
    print("\n--- Addons ---")

    # 1. addon_registry (no FK deps)
    addon_ids = await migrate_generic(
        source, target, stats, "addon_registry",
        dry_run=dry_run,
    )

    # 2. addon_permissions (FK to addon_registry)
    await migrate_generic(
        source, target, stats, "addon_permissions",
        fk_checks={"addon_id": addon_ids},
        dry_run=dry_run,
    )

    # 3. addon_tabs (FK to addon_registry)
    await migrate_generic(
        source, target, stats, "addon_tabs",
        fk_checks={"addon_id": addon_ids},
        dry_run=dry_run,
    )

    # 4. addon_storage (FK to addon_registry, user)
    await migrate_generic(
        source, target, stats, "addon_storage",
        fk_checks={"addon_id": addon_ids, "user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 5. addon_error_logs (FK to addon_registry)
    await migrate_generic(
        source, target, stats, "addon_error_logs",
        fk_checks={"addon_id": addon_ids},
        dry_run=dry_run,
    )

    # 6. addon_usage_analytics (FK to addon_registry, user)
    await migrate_generic(
        source, target, stats, "addon_usage_analytics",
        fk_checks={"addon_id": addon_ids, "user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 7. addon_reviews (FK to addon_registry, user)
    await migrate_generic(
        source, target, stats, "addon_reviews",
        fk_checks={"addon_id": addon_ids, "user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 8. global_addon_config (no FK deps)
    await migrate_generic(
        source, target, stats, "global_addon_config",
        dry_run=dry_run,
    )

    # 9. book_club_addon_config (FK to addon_registry)
    await migrate_generic(
        source, target, stats, "book_club_addon_config",
        fk_checks={"addon_id": addon_ids},
        nullable_fks={"addon_id"},
        dry_run=dry_run,
    )

    # 10. default_addon_seeds (no FK deps)
    await migrate_generic(
        source, target, stats, "default_addon_seeds",
        dry_run=dry_run,
    )


async def migrate_premium(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate premium tables."""
    print("\n--- Premium ---")

    # 1. premium_features (no FK deps)
    feature_ids = await migrate_generic(
        source, target, stats, "premium_features",
        dry_run=dry_run,
    )

    # 2. premium_requests (FK to user)
    await migrate_generic(
        source, target, stats, "premium_requests",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 3. user_premium_subscriptions (FK to user)
    await migrate_generic(
        source, target, stats, "user_premium_subscriptions",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 4. stripe_payment_intents (FK to user)
    await migrate_generic(
        source, target, stats, "stripe_payment_intents",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 5. user_upload_limits (FK to user)
    await migrate_generic(
        source, target, stats, "user_upload_limits",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )


async def migrate_public_qa(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    valid_book_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate public QA tables."""
    print("\n--- Public QA ---")

    # 1. public_qa (FK to user, book)
    qa_ids = await migrate_generic(
        source, target, stats, "public_qa",
        fk_checks={"user_id": valid_user_ids, "book_id": valid_book_ids},
        nullable_fks={"user_id", "book_id"},
        dry_run=dry_run,
    )

    # 2-5. Child tables
    for child_table in [
        "public_qa_edit_history",
        "public_qa_feedback",
        "public_qa_views",
        "public_qa_votes",
    ]:
        # Determine FK column name - could be qa_id or public_qa_id
        await migrate_generic(
            source, target, stats, child_table,
            fk_checks={"qa_id": qa_ids, "user_id": valid_user_ids},
            nullable_fks={"user_id", "qa_id"},
            dry_run=dry_run,
        )


async def migrate_suggestions(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate suggestion tables."""
    print("\n--- Suggestions ---")

    # 1. user_suggestions (FK to user)
    suggestion_ids = await migrate_generic(
        source, target, stats, "user_suggestions",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 2. suggestion_config (no FK deps)
    await migrate_generic(
        source, target, stats, "suggestion_config",
        dry_run=dry_run,
    )

    # 3. suggestion_system_config (no FK deps)
    await migrate_generic(
        source, target, stats, "suggestion_system_config",
        dry_run=dry_run,
    )

    # 4. suggestion_feedback (FK to suggestion, user)
    await migrate_generic(
        source, target, stats, "suggestion_feedback",
        fk_checks={"suggestion_id": suggestion_ids, "user_id": valid_user_ids},
        nullable_fks={"suggestion_id", "user_id"},
        dry_run=dry_run,
    )

    # 5. suggestion_notifications (FK to user)
    await migrate_generic(
        source, target, stats, "suggestion_notifications",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 6. user_suggestion_usage (FK to user)
    await migrate_generic(
        source, target, stats, "user_suggestion_usage",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )


async def migrate_rankings(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate ranking tables."""
    print("\n--- Rankings ---")

    # 1. ranking_contexts (no FK deps)
    context_ids = await migrate_generic(
        source, target, stats, "ranking_contexts",
        dry_run=dry_run,
    )

    # 2. ranking_settings (no FK deps)
    await migrate_generic(
        source, target, stats, "ranking_settings",
        dry_run=dry_run,
    )

    # 3. user_context_rankings (FK to user, context)
    await migrate_generic(
        source, target, stats, "user_context_rankings",
        fk_checks={"user_id": valid_user_ids, "context_id": context_ids},
        nullable_fks={"context_id"},
        dry_run=dry_run,
    )

    # 4. context_points_history (FK to user, context)
    await migrate_generic(
        source, target, stats, "context_points_history",
        fk_checks={"user_id": valid_user_ids, "context_id": context_ids},
        nullable_fks={"context_id"},
        dry_run=dry_run,
    )


async def migrate_admin_settings(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    dry_run: bool,
) -> None:
    """Migrate admin_settings and mystical_messages."""
    print("\n--- Admin Settings ---")

    await migrate_generic(
        source, target, stats, "admin_settings",
        dry_run=dry_run,
    )

    await migrate_generic(
        source, target, stats, "mystical_messages",
        dry_run=dry_run,
    )


async def migrate_copyright(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    valid_book_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate book_discovery_rewards."""
    print("\n--- Copyright / Discovery ---")

    await migrate_generic(
        source, target, stats, "book_discovery_rewards",
        fk_checks={"user_id": valid_user_ids, "book_id": valid_book_ids},
        nullable_fks={"user_id", "book_id"},
        dry_run=dry_run,
    )


async def migrate_expert(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate expert tables."""
    print("\n--- Expert ---")

    # 1. expert_configurations (no FK deps)
    expert_ids = await migrate_generic(
        source, target, stats, "expert_configurations",
        dry_run=dry_run,
    )

    # 2. session_participants (FK to user)
    await migrate_generic(
        source, target, stats, "session_participants",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 3. session_analytics (no strict FK deps, but may ref sessions)
    await migrate_generic(
        source, target, stats, "session_analytics",
        dry_run=dry_run,
    )


async def migrate_search_analytics(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate search_analytics."""
    print("\n--- Search Analytics ---")

    await migrate_generic(
        source, target, stats, "search_analytics",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )


async def migrate_billing(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate billing tables."""
    print("\n--- Billing ---")

    # 1. ai_billing_config (no FK deps)
    await migrate_generic(
        source, target, stats, "ai_billing_config",
        dry_run=dry_run,
    )

    # 2. user_ai_billing (FK to user)
    billing_ids = await migrate_generic(
        source, target, stats, "user_ai_billing",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 3. ai_usage_records (FK to user)
    await migrate_generic(
        source, target, stats, "ai_usage_records",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )

    # 4. monthly_billing_summaries (FK to user)
    await migrate_generic(
        source, target, stats, "monthly_billing_summaries",
        fk_checks={"user_id": valid_user_ids},
        dry_run=dry_run,
    )


async def migrate_book_club_ai(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate book club AI tables."""
    print("\n--- Book Club AI ---")

    # 1. book_club_ai_credits (no strict user FK)
    credit_ids = await migrate_generic(
        source, target, stats, "book_club_ai_credits",
        dry_run=dry_run,
    )

    # 2. book_club_ai_credit_transactions
    await migrate_generic(
        source, target, stats, "book_club_ai_credit_transactions",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 3. book_club_ai_models (no FK deps)
    await migrate_generic(
        source, target, stats, "book_club_ai_models",
        dry_run=dry_run,
    )

    # 4. book_club_ai_chat_sessions (FK to user)
    bc_session_ids = await migrate_generic(
        source, target, stats, "book_club_ai_chat_sessions",
        fk_checks={"user_id": valid_user_ids},
        nullable_fks={"user_id"},
        dry_run=dry_run,
    )

    # 5. book_club_ai_chat_messages (FK to session)
    await migrate_generic(
        source, target, stats, "book_club_ai_chat_messages",
        fk_checks={"session_id": bc_session_ids},
        dry_run=dry_run,
    )

    # 6. book_club_ai_chat_participants (FK to session, user)
    await migrate_generic(
        source, target, stats, "book_club_ai_chat_participants",
        fk_checks={"session_id": bc_session_ids, "user_id": valid_user_ids},
        dry_run=dry_run,
    )


# ========================================================================
# Main
# ========================================================================


async def main(dry_run: bool = False, export_only: bool = False) -> int:
    """Run miscellaneous migration."""
    print("\n" + "=" * 60)
    print("MIGRATION 07: Miscellaneous Tables")
    print("=" * 60)
    mode = "DRY RUN" if dry_run else ("EXPORT ONLY" if export_only else "LIVE")
    print(f"Mode: {mode}")
    print("=" * 60)

    stats = MigrationStats("07_misc")
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

        # Migrate each group in dependency order
        await migrate_issues(source, target, stats, valid_user_ids, effective_dry)
        await migrate_error_logs(source, target, stats, valid_user_ids, effective_dry)
        await migrate_addons(source, target, stats, valid_user_ids, effective_dry)
        await migrate_premium(source, target, stats, valid_user_ids, effective_dry)
        await migrate_public_qa(source, target, stats, valid_user_ids, valid_book_ids, effective_dry)
        await migrate_suggestions(source, target, stats, valid_user_ids, effective_dry)
        await migrate_rankings(source, target, stats, valid_user_ids, effective_dry)
        await migrate_admin_settings(source, target, stats, effective_dry)
        await migrate_copyright(source, target, stats, valid_user_ids, valid_book_ids, effective_dry)
        await migrate_expert(source, target, stats, valid_user_ids, effective_dry)
        await migrate_search_analytics(source, target, stats, valid_user_ids, effective_dry)
        await migrate_billing(source, target, stats, valid_user_ids, effective_dry)
        await migrate_book_club_ai(source, target, stats, valid_user_ids, effective_dry)

    finally:
        await source.close()
        if target:
            await target.close()

    stats.print_summary()
    return 0 if not stats.errors else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate miscellaneous tables from Supabase to API DB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    parser.add_argument("--export-only", action="store_true", help="Only export/count, no import")
    args = parser.parse_args()

    exit_code = asyncio.run(main(dry_run=args.dry_run, export_only=args.export_only))
    sys.exit(exit_code)
