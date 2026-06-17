"""add_gamification_tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-12 17:05:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. gamification_activities
    op.create_table(
        'gamification_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cooldown_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_daily_occurrences', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_gamification_activities_name'),
    )

    # 2. points_history
    op.create_table(
        'points_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_points_history_user_id', 'points_history', ['user_id'])

    # 3. user_activity_log
    op.create_table(
        'user_activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('activity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('points_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['activity_id'], ['gamification_activities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_user_activity_log_user_id', 'user_activity_log', ['user_id'])

    # 4. badges
    op.create_table(
        'badges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='achievement'),
        sa.Column('icon', sa.String(200), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('rarity', sa.String(20), nullable=False, server_default='common'),
        sa.Column('points_awarded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_badges_name'),
    )

    # 5. user_badges
    op.create_table(
        'user_badges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('badge_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('awarded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['badge_id'], ['badges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['awarded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),
    )
    op.create_index('idx_user_badges_user_id', 'user_badges', ['user_id'])

    # 6. ranks
    op.create_table(
        'ranks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('min_points', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('icon', sa.String(200), nullable=True),
        sa.Column('benefits', postgresql.ARRAY(sa.String(200)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_ranks_name'),
        sa.UniqueConstraint('level', name='uq_ranks_level'),
    )

    # 7. user_ranks
    op.create_table(
        'user_ranks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_points_earned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rank_achieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rank_id'], ['ranks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_ranks_user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_ranks')
    op.drop_table('ranks')
    op.drop_index('idx_user_badges_user_id', table_name='user_badges')
    op.drop_table('user_badges')
    op.drop_table('badges')
    op.drop_index('idx_user_activity_log_user_id', table_name='user_activity_log')
    op.drop_table('user_activity_log')
    op.drop_index('idx_points_history_user_id', table_name='points_history')
    op.drop_table('points_history')
    op.drop_table('gamification_activities')
