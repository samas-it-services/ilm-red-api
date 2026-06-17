"""add_extended_billing_tables

Revision ID: f6d3e4f5a6b7
Revises: e5c2d3e4f5a6
Create Date: 2026-02-12 17:21:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6d3e4f5a6b7'
down_revision: Union[str, None] = 'e5c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ai_billing_config
    op.create_table(
        'ai_billing_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False),
        sa.Column('config_value', postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key', name='uq_ai_billing_config_key'),
    )

    # 2. user_ai_billing
    op.create_table(
        'user_ai_billing',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('monthly_credit_limit', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('current_month_usage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_month_credits_remaining', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('total_lifetime_usage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_billing_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_billing_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stripe_customer_id', sa.String(100), nullable=True),
        sa.Column('auto_recharge_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_recharge_threshold', sa.Integer(), nullable=True),
        sa.Column('auto_recharge_amount', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_ai_billing_user_id'),
    )

    # 3. ai_usage_records
    op.create_table(
        'ai_usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chat_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ai_model', sa.String(50), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('billed_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('request_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_usage_records_user_id', 'ai_usage_records', ['user_id'])
    op.create_index('idx_ai_usage_records_user_created', 'ai_usage_records', ['user_id', 'created_at'])

    # 4. monthly_billing_summaries
    op.create_table(
        'monthly_billing_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('total_usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_ai_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('total_billed_cost_usd', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('credits_purchased', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('credits_granted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('credits_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('credits_remaining', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'year', 'month', name='uq_monthly_billing_user_year_month'),
    )


def downgrade() -> None:
    op.drop_table('monthly_billing_summaries')
    op.drop_index('idx_ai_usage_records_user_created', table_name='ai_usage_records')
    op.drop_index('idx_ai_usage_records_user_id', table_name='ai_usage_records')
    op.drop_table('ai_usage_records')
    op.drop_table('user_ai_billing')
    op.drop_table('ai_billing_config')
