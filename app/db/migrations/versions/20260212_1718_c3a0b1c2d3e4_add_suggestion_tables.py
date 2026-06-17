"""add_suggestion_tables

Revision ID: c3a0b1c2d3e4
Revises: b2f9a0b1c2d3
Create Date: 2026-02-12 17:18:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3a0b1c2d3e4'
down_revision: Union[str, None] = 'b2f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. user_suggestions
    op.create_table(
        'user_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suggestion_text', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('detected_language', sa.String(10), nullable=True),
        sa.Column('sentiment', sa.String(50), nullable=True),
        sa.Column('has_passage_offer', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('offered_book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('offered_book_title', sa.String(500), nullable=True),
        sa.Column('ai_response', sa.Text(), nullable=True),
        sa.Column('admin_response', sa.Text(), nullable=True),
        sa.Column('admin_responder_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('admin_response_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['admin_responder_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_user_suggestions_user', 'user_suggestions', ['user_id'])
    op.create_index('idx_user_suggestions_status', 'user_suggestions', ['status'])
    op.create_index('idx_user_suggestions_priority', 'user_suggestions', ['priority'])

    # 2. suggestion_configs
    op.create_table(
        'suggestion_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_model', sa.String(50), nullable=True),
        sa.Column('daily_limit', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_suggestion_configs_user_id'),
    )
    op.create_index('idx_suggestion_configs_user', 'suggestion_configs', ['user_id'], unique=True)

    # 3. suggestion_system_configs
    op.create_table(
        'suggestion_system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('system_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_ai_model', sa.String(50), nullable=True),
        sa.Column('default_daily_limit', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('available_models', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 4. suggestion_feedback
    op.create_table(
        'suggestion_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(50), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['suggestion_id'], ['user_suggestions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_suggestion_feedback_suggestion', 'suggestion_feedback', ['suggestion_id'])
    op.create_index('idx_suggestion_feedback_user', 'suggestion_feedback', ['user_id'])

    # 5. suggestion_notifications
    op.create_table(
        'suggestion_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['suggestion_id'], ['user_suggestions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_suggestion_notifications_user', 'suggestion_notifications', ['user_id'])
    op.create_index('idx_suggestion_notifications_unread', 'suggestion_notifications', ['user_id', 'is_read'])

    # 6. user_suggestion_usage
    op.create_table(
        'user_suggestion_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'date', name='uq_suggestion_usage_user_date'),
    )
    op.create_index('idx_suggestion_usage_user_date', 'user_suggestion_usage', ['user_id', 'date'])


def downgrade() -> None:
    op.drop_index('idx_suggestion_usage_user_date', table_name='user_suggestion_usage')
    op.drop_table('user_suggestion_usage')
    op.drop_index('idx_suggestion_notifications_unread', table_name='suggestion_notifications')
    op.drop_index('idx_suggestion_notifications_user', table_name='suggestion_notifications')
    op.drop_table('suggestion_notifications')
    op.drop_index('idx_suggestion_feedback_user', table_name='suggestion_feedback')
    op.drop_index('idx_suggestion_feedback_suggestion', table_name='suggestion_feedback')
    op.drop_table('suggestion_feedback')
    op.drop_table('suggestion_system_configs')
    op.drop_index('idx_suggestion_configs_user', table_name='suggestion_configs')
    op.drop_table('suggestion_configs')
    op.drop_index('idx_user_suggestions_priority', table_name='user_suggestions')
    op.drop_index('idx_user_suggestions_status', table_name='user_suggestions')
    op.drop_index('idx_user_suggestions_user', table_name='user_suggestions')
    op.drop_table('user_suggestions')
