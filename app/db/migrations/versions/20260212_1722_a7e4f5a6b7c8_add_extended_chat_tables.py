"""add_extended_chat_tables

Revision ID: a7e4f5a6b7c8
Revises: f6d3e4f5a6b7
Create Date: 2026-02-12 17:22:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7e4f5a6b7c8'
down_revision: Union[str, None] = 'f6d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to chat_sessions
    op.add_column('chat_sessions', sa.Column('ai_model', sa.String(50), nullable=True))
    op.add_column('chat_sessions', sa.Column('ai_provider', sa.String(50), nullable=True))
    op.add_column('chat_sessions', sa.Column('session_type', sa.String(30), nullable=False, server_default='standard'))
    op.add_column('chat_sessions', sa.Column('category', sa.String(50), nullable=True))
    op.add_column('chat_sessions', sa.Column('expert_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('chat_sessions', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('chat_sessions', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('chat_sessions', sa.Column('system_prompt', sa.Text(), nullable=True))
    op.add_column('chat_sessions', sa.Column('configuration', postgresql.JSONB(), nullable=False, server_default='{}'))
    op.add_column('chat_sessions', sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add new columns to chat_messages
    op.add_column('chat_messages', sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('chat_messages', sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'))

    # Create chat_admin_access_logs table
    op.create_table(
        'chat_admin_access_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chat_admin_access_logs_admin_id', 'chat_admin_access_logs', ['admin_user_id'])
    op.create_index('idx_chat_admin_access_logs_session_id', 'chat_admin_access_logs', ['session_id'])
    op.create_index('idx_chat_admin_access_admin_created', 'chat_admin_access_logs', ['admin_user_id', 'created_at'])

    # Create chat_encryption_keys table
    op.create_table(
        'chat_encryption_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('encrypted_key', sa.Text(), nullable=False),
        sa.Column('algorithm', sa.String(50), nullable=False, server_default='AES-256-GCM'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_chat_encryption_keys_session_id'),
    )

    # Create chat_message_ratings table
    op.create_table(
        'chat_message_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id', 'user_id', 'category', name='uq_chat_message_rating'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_chat_message_rating_value'),
    )


def downgrade() -> None:
    op.drop_table('chat_message_ratings')
    op.drop_table('chat_encryption_keys')
    op.drop_index('idx_chat_admin_access_admin_created', table_name='chat_admin_access_logs')
    op.drop_index('idx_chat_admin_access_logs_session_id', table_name='chat_admin_access_logs')
    op.drop_index('idx_chat_admin_access_logs_admin_id', table_name='chat_admin_access_logs')
    op.drop_table('chat_admin_access_logs')

    # Drop new columns from chat_messages
    op.drop_column('chat_messages', 'metadata')
    op.drop_column('chat_messages', 'is_sensitive')

    # Drop new columns from chat_sessions
    op.drop_column('chat_sessions', 'book_club_id')
    op.drop_column('chat_sessions', 'configuration')
    op.drop_column('chat_sessions', 'system_prompt')
    op.drop_column('chat_sessions', 'is_archived')
    op.drop_column('chat_sessions', 'is_public')
    op.drop_column('chat_sessions', 'expert_id')
    op.drop_column('chat_sessions', 'category')
    op.drop_column('chat_sessions', 'session_type')
    op.drop_column('chat_sessions', 'ai_provider')
    op.drop_column('chat_sessions', 'ai_model')
