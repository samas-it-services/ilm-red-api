"""add_user_profile_columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-12 17:01:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Onboarding
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))

    # Premium status
    op.add_column('users', sa.Column('is_premium_user', sa.Boolean(), nullable=False, server_default='false'))

    # Extended profile fields
    op.add_column('users', sa.Column('profile_picture_url', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('location', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))

    # Reading preferences
    op.add_column('users', sa.Column('favorite_genres', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'))
    op.add_column('users', sa.Column('reading_goal', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('language_preference', postgresql.ARRAY(sa.String(10)), nullable=False, server_default='{en}'))

    # UI and notification settings
    op.add_column('users', sa.Column('dark_mode', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('notifications_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('bookshelf_visibility', sa.String(20), nullable=False, server_default='public'))
    op.add_column('users', sa.Column('developer_mode', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('ai_chat_settings', postgresql.JSONB(), nullable=False, server_default='{}'))

    # Gamification
    op.add_column('users', sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('current_rank_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('badges_earned_count', sa.Integer(), nullable=False, server_default='0'))

    # Activity and referral
    op.add_column('users', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('referral_source', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('referred_by', postgresql.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'referred_by')
    op.drop_column('users', 'referral_source')
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'badges_earned_count')
    op.drop_column('users', 'current_rank_id')
    op.drop_column('users', 'total_points')
    op.drop_column('users', 'ai_chat_settings')
    op.drop_column('users', 'developer_mode')
    op.drop_column('users', 'bookshelf_visibility')
    op.drop_column('users', 'notifications_enabled')
    op.drop_column('users', 'dark_mode')
    op.drop_column('users', 'language_preference')
    op.drop_column('users', 'reading_goal')
    op.drop_column('users', 'favorite_genres')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'location')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'profile_picture_url')
    op.drop_column('users', 'is_premium_user')
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('users', 'onboarding_completed')
