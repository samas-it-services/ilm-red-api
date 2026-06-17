"""add_issue_tables

Revision ID: 5cf3a4b5c6d7
Revises: 4be2f3a4b5c6
Create Date: 2026-02-12 17:11:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5cf3a4b5c6d7'
down_revision: Union[str, None] = '4be2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. user_issues
    op.create_table(
        'user_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('error_code', sa.String(100), nullable=True),
        sa.Column('issue_type', sa.String(50), nullable=False, server_default='bug'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attachments', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "issue_type IN ('bug', 'feature_request', 'question', 'technical_issue', 'account_issue')",
            name='check_issue_type',
        ),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='check_issue_priority'),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'closed')", name='check_issue_status'),
    )
    op.create_index('idx_user_issues_user_id', 'user_issues', ['user_id'])
    op.create_index('idx_user_issues_status', 'user_issues', ['status'])
    op.create_index('idx_user_issues_type', 'user_issues', ['issue_type'])
    op.create_index('idx_user_issues_priority', 'user_issues', ['priority'])
    op.create_index('idx_user_issues_user_status', 'user_issues', ['user_id', 'status'])

    # 2. user_issue_responses
    op.create_table(
        'user_issue_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('responder_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attached_article_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['issue_id'], ['user_issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['responder_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_issue_responses_issue_id', 'user_issue_responses', ['issue_id'])


def downgrade() -> None:
    op.drop_index('idx_issue_responses_issue_id', table_name='user_issue_responses')
    op.drop_table('user_issue_responses')
    op.drop_index('idx_user_issues_user_status', table_name='user_issues')
    op.drop_index('idx_user_issues_priority', table_name='user_issues')
    op.drop_index('idx_user_issues_type', table_name='user_issues')
    op.drop_index('idx_user_issues_status', table_name='user_issues')
    op.drop_index('idx_user_issues_user_id', table_name='user_issues')
    op.drop_table('user_issues')
