"""add_public_qa_tables

Revision ID: a1e8f9a0b1c2
Revises: 90d7e8f9a0b1
Create Date: 2026-02-12 17:16:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1e8f9a0b1c2'
down_revision: Union[str, None] = '90d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. public_qa
    op.create_table(
        'public_qa',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('upvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('downvotes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('net_votes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('not_helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('edit_history', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_edited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['last_edited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_public_qa_status'),
        sa.CheckConstraint("visibility IN ('public', 'premium', 'admin')", name='check_public_qa_visibility'),
    )
    op.create_index('idx_public_qa_book_id', 'public_qa', ['book_id'])
    op.create_index('idx_public_qa_user_id', 'public_qa', ['user_id'])
    op.create_index('idx_public_qa_status', 'public_qa', ['status'])
    op.create_index('idx_public_qa_category', 'public_qa', ['category'])
    op.create_index('idx_public_qa_featured', 'public_qa', ['featured'])
    op.create_index('idx_public_qa_net_votes', 'public_qa', ['net_votes'])

    # 2. public_qa_edit_history
    op.create_table(
        'public_qa_edit_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qa_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edited_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('previous_question', sa.Text(), nullable=True),
        sa.Column('previous_answer', sa.Text(), nullable=True),
        sa.Column('previous_title', sa.String(500), nullable=True),
        sa.Column('previous_description', sa.Text(), nullable=True),
        sa.Column('previous_tags', postgresql.ARRAY(sa.String(50)), nullable=True),
        sa.Column('previous_category', sa.String(100), nullable=True),
        sa.Column('edit_reason', sa.Text(), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['qa_id'], ['public_qa.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['edited_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_qa_edit_history_qa_id', 'public_qa_edit_history', ['qa_id'])
    op.create_index('idx_qa_edit_history_qa_version', 'public_qa_edit_history', ['qa_id', 'version_number'])

    # 3. public_qa_feedback
    op.create_table(
        'public_qa_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qa_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['qa_id'], ['public_qa.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("feedback_type IN ('helpful', 'not_helpful')", name='check_qa_feedback_type'),
    )
    op.create_index('idx_public_qa_feedback_qa_id', 'public_qa_feedback', ['qa_id'])

    # 4. public_qa_views
    op.create_table(
        'public_qa_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('qa_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('viewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['qa_id'], ['public_qa.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['viewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_qa_views_qa_id', 'public_qa_views', ['qa_id'])
    op.create_index('idx_qa_views_qa_viewer', 'public_qa_views', ['qa_id', 'viewer_id'])
    op.create_index('idx_qa_views_qa_ip', 'public_qa_views', ['qa_id', 'ip_address'])

    # 5. public_qa_votes
    op.create_table(
        'public_qa_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_qa_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote_type', sa.String(20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['public_qa_id'], ['public_qa.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('public_qa_id', 'user_id', name='uq_public_qa_vote_user'),
        sa.CheckConstraint("vote_type IN ('upvote', 'downvote')", name='check_qa_vote_type'),
    )
    op.create_index('idx_public_qa_votes_qa_id', 'public_qa_votes', ['public_qa_id'])


def downgrade() -> None:
    op.drop_index('idx_public_qa_votes_qa_id', table_name='public_qa_votes')
    op.drop_table('public_qa_votes')
    op.drop_index('idx_qa_views_qa_ip', table_name='public_qa_views')
    op.drop_index('idx_qa_views_qa_viewer', table_name='public_qa_views')
    op.drop_index('idx_qa_views_qa_id', table_name='public_qa_views')
    op.drop_table('public_qa_views')
    op.drop_index('idx_public_qa_feedback_qa_id', table_name='public_qa_feedback')
    op.drop_table('public_qa_feedback')
    op.drop_index('idx_qa_edit_history_qa_version', table_name='public_qa_edit_history')
    op.drop_index('idx_qa_edit_history_qa_id', table_name='public_qa_edit_history')
    op.drop_table('public_qa_edit_history')
    op.drop_index('idx_public_qa_net_votes', table_name='public_qa')
    op.drop_index('idx_public_qa_featured', table_name='public_qa')
    op.drop_index('idx_public_qa_category', table_name='public_qa')
    op.drop_index('idx_public_qa_status', table_name='public_qa')
    op.drop_index('idx_public_qa_user_id', table_name='public_qa')
    op.drop_index('idx_public_qa_book_id', table_name='public_qa')
    op.drop_table('public_qa')
