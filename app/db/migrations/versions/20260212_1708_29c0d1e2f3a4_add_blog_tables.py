"""add_blog_tables

Revision ID: 29c0d1e2f3a4
Revises: 18b9c0d1e2f3
Create Date: 2026-02-12 17:08:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '29c0d1e2f3a4'
down_revision: Union[str, None] = '18b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. blog_posts
    op.create_table(
        'blog_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('slug', sa.String(600), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('featured_image_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('reading_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_blog_posts_slug'),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_blog_post_status'),
        sa.CheckConstraint("visibility IN ('public', 'private', 'members_only')", name='check_blog_post_visibility'),
    )
    op.create_index('idx_blog_posts_author_id', 'blog_posts', ['author_id'])
    op.create_index('idx_blog_posts_title', 'blog_posts', ['title'])
    op.create_index('idx_blog_posts_slug', 'blog_posts', ['slug'])
    op.create_index('idx_blog_posts_status', 'blog_posts', ['status'])
    op.create_index('idx_blog_posts_published_at', 'blog_posts', ['published_at'])
    op.create_index('idx_blog_posts_is_featured', 'blog_posts', ['is_featured'])

    # 2. blog_categories
    op.create_table(
        'blog_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_blog_categories_slug'),
    )
    op.create_index('idx_blog_categories_slug', 'blog_categories', ['slug'])

    # 3. blog_tags
    op.create_table(
        'blog_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_blog_tags_slug'),
    )
    op.create_index('idx_blog_tags_slug', 'blog_tags', ['slug'])

    # 4. blog_post_categories
    op.create_table(
        'blog_post_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['blog_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'category_id', name='uq_blog_post_category'),
    )
    op.create_index('idx_blog_post_categories_post_id', 'blog_post_categories', ['post_id'])
    op.create_index('idx_blog_post_categories_category_id', 'blog_post_categories', ['category_id'])

    # 5. blog_post_tags
    op.create_table(
        'blog_post_tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['blog_tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'tag_id', name='uq_blog_post_tag'),
    )
    op.create_index('idx_blog_post_tags_post_id', 'blog_post_tags', ['post_id'])
    op.create_index('idx_blog_post_tags_tag_id', 'blog_post_tags', ['tag_id'])

    # 6. blog_comments
    op.create_table(
        'blog_comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['blog_comments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_blog_comments_post_id', 'blog_comments', ['post_id'])
    op.create_index('idx_blog_comments_author_id', 'blog_comments', ['author_id'])
    op.create_index('idx_blog_comments_parent_id', 'blog_comments', ['parent_id'])

    # 7. blog_likes
    op.create_table(
        'blog_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('post_id', 'user_id', name='uq_blog_like_post_user'),
    )
    op.create_index('idx_blog_likes_post_id', 'blog_likes', ['post_id'])
    op.create_index('idx_blog_likes_user_id', 'blog_likes', ['user_id'])

    # 8. blog_views
    op.create_table(
        'blog_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['blog_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_blog_views_post_id', 'blog_views', ['post_id'])
    op.create_index('idx_blog_views_viewed_at', 'blog_views', ['viewed_at'])


def downgrade() -> None:
    op.drop_index('idx_blog_views_viewed_at', table_name='blog_views')
    op.drop_index('idx_blog_views_post_id', table_name='blog_views')
    op.drop_table('blog_views')
    op.drop_index('idx_blog_likes_user_id', table_name='blog_likes')
    op.drop_index('idx_blog_likes_post_id', table_name='blog_likes')
    op.drop_table('blog_likes')
    op.drop_index('idx_blog_comments_parent_id', table_name='blog_comments')
    op.drop_index('idx_blog_comments_author_id', table_name='blog_comments')
    op.drop_index('idx_blog_comments_post_id', table_name='blog_comments')
    op.drop_table('blog_comments')
    op.drop_index('idx_blog_post_tags_tag_id', table_name='blog_post_tags')
    op.drop_index('idx_blog_post_tags_post_id', table_name='blog_post_tags')
    op.drop_table('blog_post_tags')
    op.drop_index('idx_blog_post_categories_category_id', table_name='blog_post_categories')
    op.drop_index('idx_blog_post_categories_post_id', table_name='blog_post_categories')
    op.drop_table('blog_post_categories')
    op.drop_index('idx_blog_tags_slug', table_name='blog_tags')
    op.drop_table('blog_tags')
    op.drop_index('idx_blog_categories_slug', table_name='blog_categories')
    op.drop_table('blog_categories')
    op.drop_index('idx_blog_posts_is_featured', table_name='blog_posts')
    op.drop_index('idx_blog_posts_published_at', table_name='blog_posts')
    op.drop_index('idx_blog_posts_status', table_name='blog_posts')
    op.drop_index('idx_blog_posts_slug', table_name='blog_posts')
    op.drop_index('idx_blog_posts_title', table_name='blog_posts')
    op.drop_index('idx_blog_posts_author_id', table_name='blog_posts')
    op.drop_table('blog_posts')
