"""add_book_club_ai_tables

Revision ID: 90d7e8f9a0b1
Revises: 8fc6d7e8f9a0
Create Date: 2026-02-12 17:15:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '90d7e8f9a0b1'
down_revision: Union[str, None] = '8fc6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. book_club_ai_credits
    op.create_table(
        'book_club_ai_credits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('remaining_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_limit', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('reset_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('club_id', name='uq_book_club_ai_credits_club_id'),
    )
    op.create_index('idx_book_club_ai_credits_club_id', 'book_club_ai_credits', ['club_id'])

    # 2. book_club_ai_credit_transactions
    op.create_table(
        'book_club_ai_credit_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('transaction_type', sa.String(20), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_before', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_credit_transactions_club', 'book_club_ai_credit_transactions', ['club_id'])

    # 3. book_club_ai_models
    op.create_table(
        'book_club_ai_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_display_name', sa.String(200), nullable=False),
        sa.Column('model_provider', sa.String(100), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('input_cost_per_1m_tokens', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('output_cost_per_1m_tokens', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_ai_models_club_id', 'book_club_ai_models', ['club_id'])

    # 4. book_club_ai_chat_sessions
    op.create_table(
        'book_club_ai_chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_name', sa.String(300), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('participant_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_messages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_ai_chat_sessions_club_id', 'book_club_ai_chat_sessions', ['club_id'])

    # 5. book_club_ai_chat_messages
    op.create_table(
        'book_club_ai_chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['book_club_ai_chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_ai_chat_messages_session_id', 'book_club_ai_chat_messages', ['session_id'])

    # 6. book_club_ai_chat_participants
    op.create_table(
        'book_club_ai_chat_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['book_club_ai_chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'user_id', name='uq_ai_chat_participant'),
    )
    op.create_index('idx_ai_chat_participants_user', 'book_club_ai_chat_participants', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_ai_chat_participants_user', table_name='book_club_ai_chat_participants')
    op.drop_table('book_club_ai_chat_participants')
    op.drop_index('idx_book_club_ai_chat_messages_session_id', table_name='book_club_ai_chat_messages')
    op.drop_table('book_club_ai_chat_messages')
    op.drop_index('idx_book_club_ai_chat_sessions_club_id', table_name='book_club_ai_chat_sessions')
    op.drop_table('book_club_ai_chat_sessions')
    op.drop_index('idx_book_club_ai_models_club_id', table_name='book_club_ai_models')
    op.drop_table('book_club_ai_models')
    op.drop_index('idx_ai_credit_transactions_club', table_name='book_club_ai_credit_transactions')
    op.drop_table('book_club_ai_credit_transactions')
    op.drop_index('idx_book_club_ai_credits_club_id', table_name='book_club_ai_credits')
    op.drop_table('book_club_ai_credits')
