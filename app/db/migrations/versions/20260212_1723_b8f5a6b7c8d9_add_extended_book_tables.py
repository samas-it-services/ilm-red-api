"""add_extended_book_tables

Revision ID: b8f5a6b7c8d9
Revises: a7e4f5a6b7c8
Create Date: 2026-02-12 17:23:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b8f5a6b7c8d9'
down_revision: Union[str, None] = 'a7e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to books table
    op.add_column('books', sa.Column('ai_processed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('books', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('books', sa.Column('comment', sa.Text(), nullable=True))
    op.add_column('books', sa.Column('copyright_check_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('books', sa.Column('copyright_status', sa.String(50), nullable=True))
    op.add_column('books', sa.Column('user_copyright_declaration', sa.Text(), nullable=True))
    op.add_column('books', sa.Column('royalty_free_status', sa.String(50), nullable=True))
    op.add_column('books', sa.Column('download_allowed', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('books', sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'))

    # Create book_ai_processing table
    op.create_table(
        'book_ai_processing',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processing_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('ai_model', sa.String(50), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name='check_ai_processing_status',
        ),
    )
    op.create_index('idx_book_ai_processing_book_id', 'book_ai_processing', ['book_id'])
    op.create_index('idx_book_ai_processing_book_type', 'book_ai_processing', ['book_id', 'processing_type'])

    # Create book_summaries table
    op.create_table(
        'book_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('summary_type', sa.String(30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('ai_model', sa.String(50), nullable=True),
        sa.Column('chapter_number', sa.Integer(), nullable=True),
        sa.Column('chapter_title', sa.String(500), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'book_id', 'summary_type', 'language', 'chapter_number',
            name='uq_book_summary_type_lang_chapter',
        ),
    )
    op.create_index('idx_book_summaries_book_id', 'book_summaries', ['book_id'])
    op.create_index('idx_book_summaries_book_type', 'book_summaries', ['book_id', 'summary_type'])

    # Create book_page_generation_jobs table
    op.create_table(
        'book_page_generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('total_pages', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pages_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pages_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resolution', sa.String(20), nullable=False, server_default='high'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('triggered_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name='check_page_gen_status',
        ),
    )
    op.create_index('idx_page_gen_jobs_book_id', 'book_page_generation_jobs', ['book_id'])
    op.create_index('idx_page_gen_jobs_book_status', 'book_page_generation_jobs', ['book_id', 'status'])


def downgrade() -> None:
    # Drop new tables
    op.drop_index('idx_page_gen_jobs_book_status', table_name='book_page_generation_jobs')
    op.drop_index('idx_page_gen_jobs_book_id', table_name='book_page_generation_jobs')
    op.drop_table('book_page_generation_jobs')
    op.drop_index('idx_book_summaries_book_type', table_name='book_summaries')
    op.drop_index('idx_book_summaries_book_id', table_name='book_summaries')
    op.drop_table('book_summaries')
    op.drop_index('idx_book_ai_processing_book_type', table_name='book_ai_processing')
    op.drop_index('idx_book_ai_processing_book_id', table_name='book_ai_processing')
    op.drop_table('book_ai_processing')

    # Drop new columns from books
    op.drop_column('books', 'tags')
    op.drop_column('books', 'download_allowed')
    op.drop_column('books', 'royalty_free_status')
    op.drop_column('books', 'user_copyright_declaration')
    op.drop_column('books', 'copyright_status')
    op.drop_column('books', 'copyright_check_date')
    op.drop_column('books', 'comment')
    op.drop_column('books', 'is_public')
    op.drop_column('books', 'ai_processed')
