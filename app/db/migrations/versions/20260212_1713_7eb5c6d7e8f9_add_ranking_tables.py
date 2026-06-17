"""add_ranking_tables

Revision ID: 7eb5c6d7e8f9
Revises: 6da4b5c6d7e8
Create Date: 2026-02-12 17:13:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7eb5c6d7e8f9'
down_revision: Union[str, None] = '6da4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ranking_contexts
    op.create_table(
        'ranking_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("type IN ('global', 'corporate', 'book_club')", name='check_ranking_context_type'),
    )
    op.create_index('idx_ranking_contexts_type', 'ranking_contexts', ['type'])
    op.create_index('idx_ranking_contexts_active', 'ranking_contexts', ['is_active'])

    # 2. ranking_settings
    op.create_table(
        'ranking_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_type', sa.String(100), nullable=False),
        sa.Column('points_value', sa.Integer(), nullable=False),
        sa.Column('daily_limit', sa.Integer(), nullable=True),
        sa.Column('multiplier_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['context_id'], ['ranking_contexts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ranking_settings_context_id', 'ranking_settings', ['context_id'])
    op.create_index('idx_ranking_settings_context_activity', 'ranking_settings', ['context_id', 'activity_type'])

    # 3. user_context_rankings
    op.create_table(
        'user_context_rankings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank_position', sa.Integer(), nullable=False),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('percentile', sa.Float(), nullable=True),
        sa.Column('rank_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('books_uploaded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('books_reviewed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('badges_earned_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['context_id'], ['ranking_contexts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'context_id', name='uq_user_context_ranking'),
    )
    op.create_index('idx_user_context_rankings_user_id', 'user_context_rankings', ['user_id'])
    op.create_index('idx_user_context_rankings_context_id', 'user_context_rankings', ['context_id'])
    op.create_index('idx_user_context_rankings_rank', 'user_context_rankings', ['context_id', 'rank_position'])
    op.create_index('idx_user_context_rankings_points', 'user_context_rankings', ['context_id', 'total_points'])

    # 4. context_points_history
    op.create_table(
        'context_points_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['context_id'], ['ranking_contexts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_context_points_history_user_id', 'context_points_history', ['user_id'])
    op.create_index('idx_context_points_history_context_id', 'context_points_history', ['context_id'])
    op.create_index('idx_points_history_user_context', 'context_points_history', ['user_id', 'context_id'])
    op.create_index('idx_points_history_created', 'context_points_history', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_points_history_created', table_name='context_points_history')
    op.drop_index('idx_points_history_user_context', table_name='context_points_history')
    op.drop_index('idx_context_points_history_context_id', table_name='context_points_history')
    op.drop_index('idx_context_points_history_user_id', table_name='context_points_history')
    op.drop_table('context_points_history')
    op.drop_index('idx_user_context_rankings_points', table_name='user_context_rankings')
    op.drop_index('idx_user_context_rankings_rank', table_name='user_context_rankings')
    op.drop_index('idx_user_context_rankings_context_id', table_name='user_context_rankings')
    op.drop_index('idx_user_context_rankings_user_id', table_name='user_context_rankings')
    op.drop_table('user_context_rankings')
    op.drop_index('idx_ranking_settings_context_activity', table_name='ranking_settings')
    op.drop_index('idx_ranking_settings_context_id', table_name='ranking_settings')
    op.drop_table('ranking_settings')
    op.drop_index('idx_ranking_contexts_active', table_name='ranking_contexts')
    op.drop_index('idx_ranking_contexts_type', table_name='ranking_contexts')
    op.drop_table('ranking_contexts')
