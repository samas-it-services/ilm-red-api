"""add_expert_tables

Revision ID: b2f9a0b1c2d3
Revises: a1e8f9a0b1c2
Create Date: 2026-02-12 17:17:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2f9a0b1c2d3'
down_revision: Union[str, None] = 'a1e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. expert_configurations
    op.create_table(
        'expert_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('field', sa.String(200), nullable=True),
        sa.Column('traits', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('preferred_model', sa.String(50), nullable=True),
        sa.Column('preferred_provider', sa.String(50), nullable=True),
        sa.Column('system_prompt_template', sa.Text(), nullable=True),
        sa.Column('model_config_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_expert_configurations_category', 'expert_configurations', ['category'])
    op.create_index('idx_expert_configurations_active', 'expert_configurations', ['is_active'])

    # 2. session_participants
    op.create_table(
        'session_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(30), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'user_id', name='uq_session_participant'),
    )
    op.create_index('idx_session_participants_session_id', 'session_participants', ['session_id'])
    op.create_index('idx_session_participants_user', 'session_participants', ['user_id'])

    # 3. session_analytics
    op.create_table(
        'session_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expert_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('provider_used', sa.String(50), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('avg_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_satisfaction_rating', sa.Integer(), nullable=True),
        sa.Column('promoted_to_qa', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('books_referenced', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_session_analytics_session', 'session_analytics', ['session_id'])
    op.create_index('idx_session_analytics_expert', 'session_analytics', ['expert_id'])


def downgrade() -> None:
    op.drop_index('idx_session_analytics_expert', table_name='session_analytics')
    op.drop_index('idx_session_analytics_session', table_name='session_analytics')
    op.drop_table('session_analytics')
    op.drop_index('idx_session_participants_user', table_name='session_participants')
    op.drop_index('idx_session_participants_session_id', table_name='session_participants')
    op.drop_table('session_participants')
    op.drop_index('idx_expert_configurations_active', table_name='expert_configurations')
    op.drop_index('idx_expert_configurations_category', table_name='expert_configurations')
    op.drop_table('expert_configurations')
