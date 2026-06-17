"""add_premium_tables

Revision ID: 18b9c0d1e2f3
Revises: 07a8b9c0d1e2
Create Date: 2026-02-12 17:07:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '18b9c0d1e2f3'
down_revision: Union[str, None] = '07a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. premium_requests
    op.create_table(
        'premium_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('organization', sa.String(255), nullable=True),
        sa.Column('user_type', sa.String(50), nullable=True),
        sa.Column('current_usage', sa.Text(), nullable=True),
        sa.Column('interested_features', postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column('use_case', sa.Text(), nullable=True),
        sa.Column('team_size', sa.String(50), nullable=True),
        sa.Column('budget', sa.String(100), nullable=True),
        sa.Column('timeline', sa.String(100), nullable=True),
        sa.Column('additional_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'in_review')",
            name='check_premium_request_status',
        ),
    )
    op.create_index('idx_premium_requests_user_id', 'premium_requests', ['user_id'])
    op.create_index('idx_premium_requests_status', 'premium_requests', ['status'])
    op.create_index('idx_premium_requests_user_status', 'premium_requests', ['user_id', 'status'])

    # 2. premium_features
    op.create_table(
        'premium_features',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_premium_features_name'),
    )

    # 3. user_premium_subscriptions
    op.create_table(
        'user_premium_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_type', sa.String(50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_user_premium_sub_user_id', 'user_premium_subscriptions', ['user_id'])
    op.create_index('idx_user_premium_sub_active', 'user_premium_subscriptions', ['user_id', 'is_active'])

    # 4. stripe_payment_intents
    op.create_table(
        'stripe_payment_intents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(255), nullable=False),
        sa.Column('stripe_client_secret', sa.String(500), nullable=True),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('credit_amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='usd'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_payment_intent_id', name='uq_stripe_payment_intent_id'),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed', 'cancelled', 'refunded')",
            name='check_payment_intent_status',
        ),
        sa.CheckConstraint('amount > 0', name='check_payment_amount_positive'),
        sa.CheckConstraint('credit_amount > 0', name='check_credit_amount_positive'),
    )
    op.create_index('idx_stripe_payment_intents_user_id', 'stripe_payment_intents', ['user_id'])
    op.create_index('idx_stripe_payment_intents_stripe_id', 'stripe_payment_intents', ['stripe_payment_intent_id'])
    op.create_index('idx_stripe_payment_user_status', 'stripe_payment_intents', ['user_id', 'status'])

    # 5. user_upload_limits
    op.create_table(
        'user_upload_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_file_size_mb', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('total_storage_mb', sa.Integer(), nullable=False, server_default='500'),
        sa.Column('current_storage_mb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploads_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_upload_count', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('reset_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_upload_limits_user_id'),
        sa.CheckConstraint('max_file_size_mb > 0', name='check_max_file_size_positive'),
        sa.CheckConstraint('total_storage_mb > 0', name='check_total_storage_positive'),
        sa.CheckConstraint('current_storage_mb >= 0', name='check_current_storage_non_negative'),
        sa.CheckConstraint('uploads_this_month >= 0', name='check_uploads_non_negative'),
        sa.CheckConstraint('monthly_upload_count > 0', name='check_monthly_count_positive'),
    )


def downgrade() -> None:
    op.drop_table('user_upload_limits')
    op.drop_index('idx_stripe_payment_user_status', table_name='stripe_payment_intents')
    op.drop_index('idx_stripe_payment_intents_stripe_id', table_name='stripe_payment_intents')
    op.drop_index('idx_stripe_payment_intents_user_id', table_name='stripe_payment_intents')
    op.drop_table('stripe_payment_intents')
    op.drop_index('idx_user_premium_sub_active', table_name='user_premium_subscriptions')
    op.drop_index('idx_user_premium_sub_user_id', table_name='user_premium_subscriptions')
    op.drop_table('user_premium_subscriptions')
    op.drop_table('premium_features')
    op.drop_index('idx_premium_requests_user_status', table_name='premium_requests')
    op.drop_index('idx_premium_requests_status', table_name='premium_requests')
    op.drop_index('idx_premium_requests_user_id', table_name='premium_requests')
    op.drop_table('premium_requests')
