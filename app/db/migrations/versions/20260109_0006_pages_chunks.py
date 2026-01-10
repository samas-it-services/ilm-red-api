"""Page images and text chunks tables for page-first reading platform.

Revision ID: 0006
Revises: 0005
Create Date: 2026-01-09

This migration creates:
- page_images: Stores metadata for rendered PDF page images
- text_chunks: Stores chunked book text with embeddings for RAG

Core Principles:
- P1: Pages are for rendering (visual browsing)
- P2: Chunks are for thinking (AI understanding)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension for embedding storage
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create page_images table
    # Stores metadata for rendered PDF page images at different resolutions
    op.create_table(
        'page_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('thumbnail_path', sa.String(500), nullable=False),
        sa.Column('medium_path', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for page_images
    op.create_index(
        'ix_page_images_book_id',
        'page_images',
        ['book_id']
    )
    op.create_index(
        'ix_page_images_book_page',
        'page_images',
        ['book_id', 'page_number'],
        unique=True
    )
    op.create_index(
        'ix_page_images_book_order',
        'page_images',
        ['book_id', 'page_number']
    )

    # Create text_chunks table
    # Stores chunked book text with embeddings for semantic search (RAG)
    op.create_table(
        'text_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=False),
        sa.Column('page_end', sa.Integer(), nullable=False),
        # pgvector embedding column (1536 dims for OpenAI text-embedding-3-small)
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for text_chunks
    op.create_index(
        'ix_text_chunks_book_id',
        'text_chunks',
        ['book_id']
    )
    op.create_index(
        'ix_text_chunks_book_chunk',
        'text_chunks',
        ['book_id', 'chunk_index'],
        unique=True
    )
    op.create_index(
        'ix_text_chunks_book_order',
        'text_chunks',
        ['book_id', 'chunk_index']
    )

    # Alter the embedding column to use vector type
    # This requires the pgvector extension which we created above
    op.execute('ALTER TABLE text_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)')

    # Create IVFFlat index for approximate nearest neighbor search
    # Note: This index works best when the table has data
    # For empty tables, it will be created but may need to be rebuilt after data load
    op.execute('''
        CREATE INDEX ix_text_chunks_embedding
        ON text_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_text_chunks_embedding', table_name='text_chunks')
    op.drop_index('ix_text_chunks_book_order', table_name='text_chunks')
    op.drop_index('ix_text_chunks_book_chunk', table_name='text_chunks')
    op.drop_index('ix_text_chunks_book_id', table_name='text_chunks')

    # Drop text_chunks table
    op.drop_table('text_chunks')

    # Drop page_images indexes
    op.drop_index('ix_page_images_book_order', table_name='page_images')
    op.drop_index('ix_page_images_book_page', table_name='page_images')
    op.drop_index('ix_page_images_book_id', table_name='page_images')

    # Drop page_images table
    op.drop_table('page_images')

    # Note: We don't drop the pgvector extension as other tables might use it
