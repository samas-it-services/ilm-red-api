"""add_help_tables

Revision ID: 3ad1e2f3a4b5
Revises: 29c0d1e2f3a4
Create Date: 2026-02-12 17:09:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3ad1e2f3a4b5'
down_revision: Union[str, None] = '29c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. help_categories
    op.create_table(
        'help_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_help_categories_slug'),
    )
    op.create_index('idx_help_categories_slug', 'help_categories', ['slug'])
    op.create_index('idx_help_categories_sort_order', 'help_categories', ['sort_order'])

    # 2. help_articles
    op.create_table(
        'help_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(300), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title_en', sa.String(500), nullable=False),
        sa.Column('content_en', sa.Text(), nullable=False),
        sa.Column('title_ur', sa.String(500), nullable=True),
        sa.Column('content_ur', sa.Text(), nullable=True),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True, server_default='{}'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('not_helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['help_categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_help_articles_slug'),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_help_article_status'),
        sa.CheckConstraint("visibility IN ('public', 'private', 'members_only')", name='check_help_article_visibility'),
    )
    op.create_index('idx_help_articles_category_id', 'help_articles', ['category_id'])
    op.create_index('idx_help_articles_slug', 'help_articles', ['slug'])
    op.create_index('idx_help_articles_author_id', 'help_articles', ['author_id'])
    op.create_index('idx_help_articles_title_en', 'help_articles', ['title_en'])
    op.create_index('idx_help_articles_status', 'help_articles', ['status'])
    op.create_index('idx_help_articles_sort_order', 'help_articles', ['sort_order'])
    op.create_index('idx_help_articles_published_at', 'help_articles', ['published_at'])

    # 3. help_article_views
    op.create_table(
        'help_article_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['help_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_help_article_views_article_id', 'help_article_views', ['article_id'])
    op.create_index('idx_help_article_views_viewed_at', 'help_article_views', ['viewed_at'])

    # 4. help_article_feedbacks
    op.create_table(
        'help_article_feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(20), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['help_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("feedback_type IN ('helpful', 'not_helpful')", name='check_help_feedback_type'),
    )
    op.create_index('idx_help_article_feedbacks_article_id', 'help_article_feedbacks', ['article_id'])

    # 5. help_article_shares
    op.create_table(
        'help_article_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('share_method', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('shared_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['help_articles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_help_article_shares_article_id', 'help_article_shares', ['article_id'])

    # 6. help_article_screenshots
    op.create_table(
        'help_article_screenshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('alt_text', sa.String(255), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['article_id'], ['help_articles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_help_article_screenshots_article_id', 'help_article_screenshots', ['article_id'])


def downgrade() -> None:
    op.drop_index('idx_help_article_screenshots_article_id', table_name='help_article_screenshots')
    op.drop_table('help_article_screenshots')
    op.drop_index('idx_help_article_shares_article_id', table_name='help_article_shares')
    op.drop_table('help_article_shares')
    op.drop_index('idx_help_article_feedbacks_article_id', table_name='help_article_feedbacks')
    op.drop_table('help_article_feedbacks')
    op.drop_index('idx_help_article_views_viewed_at', table_name='help_article_views')
    op.drop_index('idx_help_article_views_article_id', table_name='help_article_views')
    op.drop_table('help_article_views')
    op.drop_index('idx_help_articles_published_at', table_name='help_articles')
    op.drop_index('idx_help_articles_sort_order', table_name='help_articles')
    op.drop_index('idx_help_articles_status', table_name='help_articles')
    op.drop_index('idx_help_articles_title_en', table_name='help_articles')
    op.drop_index('idx_help_articles_author_id', table_name='help_articles')
    op.drop_index('idx_help_articles_slug', table_name='help_articles')
    op.drop_index('idx_help_articles_category_id', table_name='help_articles')
    op.drop_table('help_articles')
    op.drop_index('idx_help_categories_sort_order', table_name='help_categories')
    op.drop_index('idx_help_categories_slug', table_name='help_categories')
    op.drop_table('help_categories')
