"""add_addon_tables

Revision ID: 8fc6d7e8f9a0
Revises: 7eb5c6d7e8f9
Create Date: 2026-02-12 17:14:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8fc6d7e8f9a0'
down_revision: Union[str, None] = '7eb5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. addon_registry
    op.create_table(
        'addon_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(200), nullable=False),
        sa.Column('version', sa.String(50), nullable=False, server_default='1.0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(500), nullable=True),
        sa.Column('author', sa.String(200), nullable=True),
        sa.Column('author_email', sa.String(255), nullable=True),
        sa.Column('license', sa.String(100), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('entry_point', sa.String(500), nullable=True),
        sa.Column('manifest_url', sa.Text(), nullable=True),
        sa.Column('bundle_url', sa.Text(), nullable=True),
        sa.Column('config_schema', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('permissions', postgresql.ARRAY(sa.String(100)), nullable=False, server_default='{}'),
        sa.Column('is_official', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_free', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('price', sa.Numeric(10, 2), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_addon_registry_slug'),
        sa.CheckConstraint("status IN ('active', 'deprecated', 'disabled')", name='check_addon_registry_status'),
    )
    op.create_index('idx_addon_registry_slug', 'addon_registry', ['slug'])
    op.create_index('idx_addon_registry_category', 'addon_registry', ['category'])
    op.create_index('idx_addon_registry_status', 'addon_registry', ['status'])

    # 2. addon_permissions
    op.create_table(
        'addon_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('is_dangerous', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_addon_permissions_name'),
    )

    # 3. global_addon_config
    op.create_table(
        'global_addon_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_installations_per_club', sa.Integer(), nullable=True),
        sa.Column('default_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('configured_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addon_registry.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['configured_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('addon_id', name='uq_global_addon_config_addon_id'),
    )

    # 4. book_club_addon_config
    op.create_table(
        'book_club_addon_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_enabled_by_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('can_be_disabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('max_installations', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('configured_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addon_registry.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['configured_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('addon_id', 'book_club_id', name='uq_club_addon_config'),
    )
    op.create_index('idx_club_addon_config_club', 'book_club_addon_config', ['book_club_id'])

    # 5. addon_tabs
    op.create_table(
        'addon_tabs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_addon_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tab_id', sa.String(100), nullable=False),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('icon', sa.String(200), nullable=True),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['book_club_addon_id'], ['book_club_addon_config.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6. addon_storage
    op.create_table(
        'addon_storage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addon_registry.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('addon_id', 'book_club_id', 'key', name='uq_addon_storage_key'),
    )
    op.create_index('idx_addon_storage_addon_club', 'addon_storage', ['addon_id', 'book_club_id'])

    # 7. addon_error_logs
    op.create_table(
        'addon_error_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_addon_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('error_type', sa.String(100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addon_registry.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_addon_error_logs_addon_id', 'addon_error_logs', ['addon_id'])

    # 8. addon_usage_analytics
    op.create_table(
        'addon_usage_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_addon_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_addon_usage_user', 'addon_usage_analytics', ['user_id'])
    op.create_index('idx_addon_usage_action', 'addon_usage_analytics', ['action'])

    # 9. addon_reviews
    op.create_table(
        'addon_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addon_registry.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('addon_id', 'user_id', name='uq_addon_review_user'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_addon_review_rating'),
    )
    op.create_index('idx_addon_reviews_addon', 'addon_reviews', ['addon_id'])

    # 10. default_addon_seeds
    op.create_table(
        'default_addon_seeds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_slug', sa.String(200), nullable=False),
        sa.Column('is_enabled_by_default', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('default_addon_seeds')
    op.drop_index('idx_addon_reviews_addon', table_name='addon_reviews')
    op.drop_table('addon_reviews')
    op.drop_index('idx_addon_usage_action', table_name='addon_usage_analytics')
    op.drop_index('idx_addon_usage_user', table_name='addon_usage_analytics')
    op.drop_table('addon_usage_analytics')
    op.drop_index('idx_addon_error_logs_addon_id', table_name='addon_error_logs')
    op.drop_table('addon_error_logs')
    op.drop_index('idx_addon_storage_addon_club', table_name='addon_storage')
    op.drop_table('addon_storage')
    op.drop_table('addon_tabs')
    op.drop_index('idx_club_addon_config_club', table_name='book_club_addon_config')
    op.drop_table('book_club_addon_config')
    op.drop_table('global_addon_config')
    op.drop_table('addon_permissions')
    op.drop_index('idx_addon_registry_status', table_name='addon_registry')
    op.drop_index('idx_addon_registry_category', table_name='addon_registry')
    op.drop_index('idx_addon_registry_slug', table_name='addon_registry')
    op.drop_table('addon_registry')
