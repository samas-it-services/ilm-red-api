"""add_announcement_tables

Revision ID: 4be2f3a4b5c6
Revises: 3ad1e2f3a4b5
Create Date: 2026-02-12 17:10:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4be2f3a4b5c6'
down_revision: Union[str, None] = '3ad1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. feature_announcements
    op.create_table(
        'feature_announcements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('slug', sa.String(600), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('featured_image_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='normal'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_feature_announcements_slug'),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_announcement_status'),
        sa.CheckConstraint("priority IN ('low', 'normal', 'high', 'critical')", name='check_announcement_priority'),
    )
    op.create_index('idx_feature_announcements_title', 'feature_announcements', ['title'])
    op.create_index('idx_feature_announcements_slug', 'feature_announcements', ['slug'])
    op.create_index('idx_feature_announcements_status', 'feature_announcements', ['status'])
    op.create_index('idx_feature_announcements_published_at', 'feature_announcements', ['published_at'])
    op.create_index('idx_feature_announcements_priority', 'feature_announcements', ['priority'])
    op.create_index('idx_feature_announcements_is_pinned', 'feature_announcements', ['is_pinned'])

    # 2. feature_announcement_views
    op.create_table(
        'feature_announcement_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('announcement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['announcement_id'], ['feature_announcements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_announcement_views_announcement_id', 'feature_announcement_views', ['announcement_id'])
    op.create_index('idx_announcement_views_user_id', 'feature_announcement_views', ['user_id'])
    op.create_index('idx_announcement_views_viewed_at', 'feature_announcement_views', ['viewed_at'])


def downgrade() -> None:
    op.drop_index('idx_announcement_views_viewed_at', table_name='feature_announcement_views')
    op.drop_index('idx_announcement_views_user_id', table_name='feature_announcement_views')
    op.drop_index('idx_announcement_views_announcement_id', table_name='feature_announcement_views')
    op.drop_table('feature_announcement_views')
    op.drop_index('idx_feature_announcements_is_pinned', table_name='feature_announcements')
    op.drop_index('idx_feature_announcements_priority', table_name='feature_announcements')
    op.drop_index('idx_feature_announcements_published_at', table_name='feature_announcements')
    op.drop_index('idx_feature_announcements_status', table_name='feature_announcements')
    op.drop_index('idx_feature_announcements_slug', table_name='feature_announcements')
    op.drop_index('idx_feature_announcements_title', table_name='feature_announcements')
    op.drop_table('feature_announcements')
