"""Books tables migration.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create books table
    op.create_table(
        'books',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Metadata
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='other'),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('isbn', sa.String(20), nullable=True),
        # Visibility
        sa.Column('visibility', sa.String(20), nullable=False, server_default='private'),
        # File information
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        # Book details
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('cover_url', sa.String(500), nullable=True),
        # Processing status
        sa.Column('status', sa.String(20), nullable=False, server_default='processing'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        # Stats (cached aggregations)
        sa.Column('stats', postgresql.JSONB(), nullable=False,
                  server_default='{"views": 0, "downloads": 0, "rating_count": 0, "rating_avg": 0.0}'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('uploading', 'processing', 'ready', 'failed')", name='check_book_status'),
        sa.CheckConstraint("visibility IN ('public', 'private', 'friends')", name='check_book_visibility'),
    )

    # Indexes for books table
    op.create_index('idx_books_owner_id', 'books', ['owner_id'])
    op.create_index('idx_books_title', 'books', ['title'])
    op.create_index('idx_books_file_hash', 'books', ['file_hash'])
    op.create_index('idx_books_visibility', 'books', ['visibility'])
    op.create_index('idx_books_category', 'books', ['category'])
    op.create_index('idx_books_owner_hash', 'books', ['owner_id', 'file_hash'])

    # Create ratings table
    op.create_table(
        'ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_id', 'user_id', name='uq_rating_book_user'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_value'),
    )

    # Indexes for ratings table
    op.create_index('idx_ratings_book_id', 'ratings', ['book_id'])

    # Create favorites table
    op.create_table(
        'favorites',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'book_id'),
    )

    # Indexes for favorites table
    op.create_index('idx_favorites_user_id', 'favorites', ['user_id'])


def downgrade() -> None:
    op.drop_table('favorites')
    op.drop_table('ratings')
    op.drop_table('books')
