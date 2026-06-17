"""add_error_logs

Revision ID: 07a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-12 17:06:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '07a8b9c0d1e2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'error_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('error_code', sa.String(20), nullable=False),
        sa.Column('error_type', sa.String(100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('request_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('severity', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('error_code', name='uq_error_logs_error_code'),
    )
    op.create_index('idx_error_logs_error_code', 'error_logs', ['error_code'])
    op.create_index('idx_error_logs_user_id', 'error_logs', ['user_id'])
    op.create_index('idx_error_logs_severity', 'error_logs', ['severity'])
    op.create_index('idx_error_logs_resolved', 'error_logs', ['resolved'])
    op.create_index('idx_error_logs_created_at', 'error_logs', ['created_at'])
    op.create_index('idx_error_logs_error_type', 'error_logs', ['error_type'])


def downgrade() -> None:
    op.drop_index('idx_error_logs_error_type', table_name='error_logs')
    op.drop_index('idx_error_logs_created_at', table_name='error_logs')
    op.drop_index('idx_error_logs_resolved', table_name='error_logs')
    op.drop_index('idx_error_logs_severity', table_name='error_logs')
    op.drop_index('idx_error_logs_user_id', table_name='error_logs')
    op.drop_index('idx_error_logs_error_code', table_name='error_logs')
    op.drop_table('error_logs')
