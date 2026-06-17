#!/usr/bin/env python3
"""Migrate content data from Supabase to API PostgreSQL.

Tables migrated:
  Blog (8 tables):
    blog_categories, blog_tags, blog_posts, blog_post_categories,
    blog_post_tags, blog_comments, blog_likes, blog_views
  Help (6 tables):
    help_categories, help_articles, help_article_views,
    help_article_feedback, help_article_shares, help_article_screenshots
  Announcements (2 tables):
    feature_announcements, feature_announcement_views
  Quotes (2 tables):
    quotes, quote_views

Usage:
    python scripts/migrations/05_migrate_content.py
    python scripts/migrations/05_migrate_content.py --dry-run
    python scripts/migrations/05_migrate_content.py --export-only

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
# Blog tables
# ========================================================================


async def migrate_blog_categories(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Migrate blog_categories."""
    table = "blog_categories"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_categories (id, name, slug, description, parent_id,
                    sort_order, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                row.get("name"),
                row.get("slug"),
                row.get("description"),
                safe_uuid(row.get("parent_id")),
                row.get("sort_order", 0),
                row.get("is_active", True),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_blog_tags(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Migrate blog_tags."""
    table = "blog_tags"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_tags (id, name, slug, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                row.get("name"),
                row.get("slug"),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_blog_posts(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> set[str]:
    """Migrate blog_posts (author_id FK to users)."""
    table = "blog_posts"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        author_id = str(row["author_id"]) if row.get("author_id") else None

        # Skip if author doesn't exist in target
        if author_id and author_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_posts (id, author_id, title, slug, content, excerpt,
                    cover_image_url, status, is_featured, view_count, like_count,
                    comment_count, published_at, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(author_id),
                row.get("title"),
                row.get("slug"),
                row.get("content"),
                row.get("excerpt"),
                row.get("cover_image_url"),
                row.get("status", "draft"),
                row.get("is_featured", False),
                row.get("view_count", 0),
                row.get("like_count", 0),
                row.get("comment_count", 0),
                parse_dt(row.get("published_at")),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_blog_post_categories(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_post_ids: set[str],
    valid_category_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate blog_post_categories junction table."""
    table = "blog_post_categories"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY post_id, category_id")

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        post_id = str(row["post_id"]) if row.get("post_id") else None
        category_id = str(row["category_id"]) if row.get("category_id") else None

        if not post_id or post_id not in valid_post_ids:
            stats.track(table, skipped=1)
            continue
        if not category_id or category_id not in valid_category_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_post_categories (post_id, category_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                safe_uuid(post_id),
                safe_uuid(category_id),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


async def migrate_blog_post_tags(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_post_ids: set[str],
    valid_tag_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate blog_post_tags junction table."""
    table = "blog_post_tags"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY post_id, tag_id")

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        post_id = str(row["post_id"]) if row.get("post_id") else None
        tag_id = str(row["tag_id"]) if row.get("tag_id") else None

        if not post_id or post_id not in valid_post_ids:
            stats.track(table, skipped=1)
            continue
        if not tag_id or tag_id not in valid_tag_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_post_tags (post_id, tag_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                safe_uuid(post_id),
                safe_uuid(tag_id),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


async def migrate_blog_comments(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_post_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate blog_comments (author_id FK, parent_id self-FK).

    Comments are migrated in two passes:
      1) Top-level comments (parent_id IS NULL)
      2) Replies (parent_id IS NOT NULL)
    """
    table = "blog_comments"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return

    # Fetch all comments ordered so parents come first
    rows = await fetch_paginated(
        source,
        f"SELECT * FROM {table} ORDER BY COALESCE(parent_id, id), id",
    )

    if not rows:
        print(f"  No rows found in {table}")
        return

    stats.track(table, exported=len(rows))
    valid_comment_ids: set[str] = set()

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        author_id = str(row["author_id"]) if row.get("author_id") else None
        post_id = str(row["post_id"]) if row.get("post_id") else None
        parent_id = str(row["parent_id"]) if row.get("parent_id") else None

        # Skip if post doesn't exist
        if not post_id or post_id not in valid_post_ids:
            stats.track(table, skipped=1)
            continue

        # Skip if author doesn't exist
        if author_id and author_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        # Skip replies whose parent was skipped
        if parent_id and parent_id not in valid_comment_ids:
            stats.track(table, skipped=1)
            continue

        valid_comment_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_comments (id, post_id, author_id, parent_id, content,
                    is_approved, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(post_id),
                safe_uuid(author_id),
                safe_uuid(parent_id),
                row.get("content"),
                row.get("is_approved", True),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")


async def migrate_blog_likes(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_post_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate blog_likes (user_id FK)."""
    table = "blog_likes"
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
        user_id = str(row["user_id"]) if row.get("user_id") else None
        post_id = str(row["post_id"]) if row.get("post_id") else None

        if not user_id or user_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue
        if not post_id or post_id not in valid_post_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_likes (id, post_id, user_id, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(post_id),
                safe_uuid(user_id),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


async def migrate_blog_views(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_post_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate blog_views (user_id nullable - anonymous views allowed)."""
    table = "blog_views"
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
        post_id = str(row["post_id"]) if row.get("post_id") else None
        user_id = str(row["user_id"]) if row.get("user_id") else None

        if not post_id or post_id not in valid_post_ids:
            stats.track(table, skipped=1)
            continue

        # user_id is nullable (anonymous views), but if set must be valid
        if user_id and user_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO blog_views (id, post_id, user_id, ip_address,
                    user_agent, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(post_id),
                safe_uuid(user_id),
                row.get("ip_address"),
                row.get("user_agent"),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Help tables
# ========================================================================


async def migrate_help_categories(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Migrate help_categories."""
    table = "help_categories"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO help_categories (id, name, slug, description, icon,
                    parent_id, sort_order, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                row.get("name"),
                row.get("slug"),
                row.get("description"),
                row.get("icon"),
                safe_uuid(row.get("parent_id")),
                row.get("sort_order", 0),
                row.get("is_active", True),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_help_articles(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_category_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> set[str]:
    """Migrate help_articles with multi-language fields."""
    table = "help_articles"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        author_id = str(row["author_id"]) if row.get("author_id") else None
        category_id = str(row["category_id"]) if row.get("category_id") else None

        # Skip if author doesn't exist
        if author_id and author_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        # Skip if category doesn't exist
        if category_id and category_id not in valid_category_ids:
            stats.track(table, skipped=1)
            continue

        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO help_articles (id, category_id, author_id, slug, status,
                    title_en, content_en, title_ur, content_ur, title_ar, content_ar,
                    title_hi, content_hi,
                    is_featured, sort_order, view_count, helpful_count, not_helpful_count,
                    created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18, $19, $20)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(category_id),
                safe_uuid(author_id),
                row.get("slug"),
                row.get("status", "published"),
                row.get("title_en") or row.get("title"),
                row.get("content_en") or row.get("content"),
                row.get("title_ur"),
                row.get("content_ur"),
                row.get("title_ar"),
                row.get("content_ar"),
                row.get("title_hi"),
                row.get("content_hi"),
                row.get("is_featured", False),
                row.get("sort_order", 0),
                row.get("view_count", 0),
                row.get("helpful_count", 0),
                row.get("not_helpful_count", 0),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_help_article_child(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    table: str,
    valid_article_ids: set[str],
    dry_run: bool,
) -> None:
    """Generic migration for help article child tables (views, feedback, shares, screenshots)."""
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
        article_id = str(row["article_id"]) if row.get("article_id") else None

        if not article_id or article_id not in valid_article_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            # Build dynamic insert from row keys
            cols = [k for k in row.keys()]
            placeholders = [f"${i+1}" for i in range(len(cols))]
            values = []
            for col in cols:
                val = row[col]
                # Convert UUIDs
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
# Announcements
# ========================================================================


async def migrate_feature_announcements(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    dry_run: bool,
) -> set[str]:
    """Migrate feature_announcements."""
    table = "feature_announcements"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO feature_announcements (id, title, content, announcement_type,
                    priority, is_active, start_date, end_date, target_roles,
                    created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                row.get("title"),
                row.get("content"),
                row.get("announcement_type", "feature"),
                row.get("priority", 0),
                row.get("is_active", True),
                parse_dt(row.get("start_date")),
                parse_dt(row.get("end_date")),
                row.get("target_roles"),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_feature_announcement_views(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_announcement_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate feature_announcement_views."""
    table = "feature_announcement_views"
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
        announcement_id = str(row["announcement_id"]) if row.get("announcement_id") else None
        user_id = str(row["user_id"]) if row.get("user_id") else None

        if not announcement_id or announcement_id not in valid_announcement_ids:
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
                INSERT INTO feature_announcement_views (id, announcement_id, user_id,
                    viewed_at, dismissed_at, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(announcement_id),
                safe_uuid(user_id),
                parse_dt(row.get("viewed_at")),
                parse_dt(row.get("dismissed_at")),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Quotes
# ========================================================================


async def migrate_quotes(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_user_ids: set[str],
    dry_run: bool,
) -> set[str]:
    """Migrate quotes (created_by FK to users)."""
    table = "quotes"
    print(f"\nMigrating {table}...")

    if not await table_exists(source, table):
        print(f"  Source table {table} does not exist - skipping")
        return set()

    rows = await fetch_paginated(source, f"SELECT * FROM {table} ORDER BY id")
    valid_ids: set[str] = set()

    if not rows:
        print(f"  No rows found in {table}")
        return valid_ids

    stats.track(table, exported=len(rows))

    for row in tqdm(rows, desc=f"  {table}"):
        row_id = str(row["id"])
        created_by = str(row["created_by"]) if row.get("created_by") else None

        # Skip if created_by user doesn't exist
        if created_by and created_by not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        valid_ids.add(row_id)

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO quotes (id, text, author, source, category,
                    language, created_by, is_active, view_count,
                    created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                row.get("text"),
                row.get("author"),
                row.get("source"),
                row.get("category"),
                row.get("language", "en"),
                safe_uuid(created_by),
                row.get("is_active", True),
                row.get("view_count", 0),
                parse_dt(row.get("created_at")),
                parse_dt(row.get("updated_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table} {row_id}: {e}")

    print(f"  {table}: {stats.tables[table]}")
    return valid_ids


async def migrate_quote_views(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    stats: MigrationStats,
    valid_quote_ids: set[str],
    valid_user_ids: set[str],
    dry_run: bool,
) -> None:
    """Migrate quote_views."""
    table = "quote_views"
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
        quote_id = str(row["quote_id"]) if row.get("quote_id") else None
        user_id = str(row["user_id"]) if row.get("user_id") else None

        if not quote_id or quote_id not in valid_quote_ids:
            stats.track(table, skipped=1)
            continue

        # user_id is nullable (anonymous views)
        if user_id and user_id not in valid_user_ids:
            stats.track(table, skipped=1)
            continue

        if dry_run:
            stats.track(table, imported=1)
            continue

        try:
            await target.execute(
                """
                INSERT INTO quote_views (id, quote_id, user_id, ip_address,
                    created_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
                """,
                safe_uuid(row["id"]),
                safe_uuid(quote_id),
                safe_uuid(user_id),
                row.get("ip_address"),
                parse_dt(row.get("created_at")),
            )
            stats.track(table, imported=1)
        except Exception as e:
            stats.track(table, skipped=1)
            stats.errors.append(f"{table}: {e}")

    print(f"  {table}: {stats.tables[table]}")


# ========================================================================
# Main
# ========================================================================


async def main(dry_run: bool = False, export_only: bool = False) -> int:
    """Run content migration."""
    print("\n" + "=" * 60)
    print("MIGRATION 05: Content (Blog, Help, Announcements, Quotes)")
    print("=" * 60)
    mode = "DRY RUN" if dry_run else ("EXPORT ONLY" if export_only else "LIVE")
    print(f"Mode: {mode}")
    print("=" * 60)

    stats = MigrationStats("05_content")
    source = await connect_source()

    try:
        target = None
        if not export_only:
            target = await connect_target()

        # Build valid FK sets from target
        valid_user_ids: set[str] = set()
        if target:
            valid_user_ids = await get_valid_user_ids(target)
            print(f"  Found {len(valid_user_ids)} valid users in target")

        # ------------------------------------------------------------------
        # Blog
        # ------------------------------------------------------------------
        print("\n--- Blog ---")
        blog_category_ids = await migrate_blog_categories(source, target, stats, dry_run or export_only)
        blog_tag_ids = await migrate_blog_tags(source, target, stats, dry_run or export_only)
        blog_post_ids = await migrate_blog_posts(source, target, stats, valid_user_ids, dry_run or export_only)
        await migrate_blog_post_categories(source, target, stats, blog_post_ids, blog_category_ids, dry_run or export_only)
        await migrate_blog_post_tags(source, target, stats, blog_post_ids, blog_tag_ids, dry_run or export_only)
        await migrate_blog_comments(source, target, stats, blog_post_ids, valid_user_ids, dry_run or export_only)
        await migrate_blog_likes(source, target, stats, blog_post_ids, valid_user_ids, dry_run or export_only)
        await migrate_blog_views(source, target, stats, blog_post_ids, valid_user_ids, dry_run or export_only)

        # ------------------------------------------------------------------
        # Help
        # ------------------------------------------------------------------
        print("\n--- Help ---")
        help_category_ids = await migrate_help_categories(source, target, stats, dry_run or export_only)
        help_article_ids = await migrate_help_articles(
            source, target, stats, help_category_ids, valid_user_ids, dry_run or export_only,
        )
        for child_table in [
            "help_article_views",
            "help_article_feedback",
            "help_article_shares",
            "help_article_screenshots",
        ]:
            await migrate_help_article_child(source, target, stats, child_table, help_article_ids, dry_run or export_only)

        # ------------------------------------------------------------------
        # Announcements
        # ------------------------------------------------------------------
        print("\n--- Announcements ---")
        announcement_ids = await migrate_feature_announcements(source, target, stats, dry_run or export_only)
        await migrate_feature_announcement_views(
            source, target, stats, announcement_ids, valid_user_ids, dry_run or export_only,
        )

        # ------------------------------------------------------------------
        # Quotes
        # ------------------------------------------------------------------
        print("\n--- Quotes ---")
        quote_ids = await migrate_quotes(source, target, stats, valid_user_ids, dry_run or export_only)
        await migrate_quote_views(source, target, stats, quote_ids, valid_user_ids, dry_run or export_only)

    finally:
        await source.close()
        if target:
            await target.close()

    stats.print_summary()
    return 0 if not stats.errors else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate content data (blog, help, announcements, quotes) from Supabase to API DB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate without writing")
    parser.add_argument("--export-only", action="store_true", help="Only export/count, no import")
    args = parser.parse_args()

    exit_code = asyncio.run(main(dry_run=args.dry_run, export_only=args.export_only))
    sys.exit(exit_code)
