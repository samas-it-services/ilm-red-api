"""Billing tables migration.

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-09

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_credits table
    op.create_table(
        'user_credits',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('balance_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lifetime_usage_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('free_credits_remaining', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('free_credits_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.CheckConstraint('balance_cents >= 0', name='check_balance_non_negative'),
        sa.CheckConstraint('free_credits_remaining >= 0', name='check_free_credits_non_negative'),
    )

    # Create billing_transactions table
    op.create_table(
        'billing_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation_type', sa.String(30), nullable=False),
        sa.Column('operation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('model', sa.String(50), nullable=False),
        sa.Column('tokens_input', sa.Integer(), nullable=False),
        sa.Column('tokens_output', sa.Integer(), nullable=False),
        sa.Column('cost_cents', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "operation_type IN ('chat', 'summary', 'search', 'embedding', 'flashcards', 'quiz', 'credit_purchase', 'credit_refund', 'free_credit')",
            name='check_operation_type'
        ),
    )

    # Indexes for billing_transactions table
    op.create_index(
        'idx_billing_transactions_user_created',
        'billing_transactions',
        ['user_id', sa.text('created_at DESC')]
    )
    op.create_index(
        'idx_billing_transactions_operation',
        'billing_transactions',
        ['operation_type', 'operation_id'],
        postgresql_where=sa.text('operation_id IS NOT NULL')
    )

    # Create usage_limits table
    op.create_table(
        'usage_limits',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('daily_tokens_limit', sa.Integer(), nullable=False, server_default='100000'),
        sa.Column('daily_tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('daily_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_cost_limit_cents', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('monthly_cost_used_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.CheckConstraint('daily_tokens_limit >= 0', name='check_daily_limit_non_negative'),
        sa.CheckConstraint('monthly_cost_limit_cents >= 0', name='check_monthly_limit_non_negative'),
    )


def downgrade() -> None:
    op.drop_table('usage_limits')
    op.drop_table('billing_transactions')
    op.drop_table('user_credits')
