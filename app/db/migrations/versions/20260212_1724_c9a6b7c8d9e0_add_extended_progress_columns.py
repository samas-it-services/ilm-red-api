"""add_extended_progress_columns

Revision ID: c9a6b7c8d9e0
Revises: b8f5a6b7c8d9
Create Date: 2026-02-12 17:24:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9a6b7c8d9e0'
down_revision: Union[str, None] = 'b8f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to reading_progress table
    op.add_column('reading_progress', sa.Column('book_format', sa.String(20), nullable=True))
    op.add_column('reading_progress', sa.Column('reading_mode', sa.String(20), nullable=True))
    op.add_column('reading_progress', sa.Column('scale', sa.Float(), nullable=True))
    op.add_column('reading_progress', sa.Column('zoom_level', sa.Float(), nullable=True))
    op.add_column('reading_progress', sa.Column('viewport_x', sa.Float(), nullable=True))
    op.add_column('reading_progress', sa.Column('viewport_y', sa.Float(), nullable=True))
    op.add_column('reading_progress', sa.Column('chapter_title', sa.String(500), nullable=True))
    op.add_column('reading_progress', sa.Column('chapter_href', sa.String(500), nullable=True))
    op.add_column('reading_progress', sa.Column('epub_location', postgresql.JSONB(), nullable=True))
    op.add_column('reading_progress', sa.Column('last_viewed_pages', postgresql.ARRAY(sa.Integer()), nullable=False, server_default='{}'))
    op.add_column('reading_progress', sa.Column('session_reading_time', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('reading_progress', sa.Column('reading_time_minutes', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('reading_progress', 'reading_time_minutes')
    op.drop_column('reading_progress', 'session_reading_time')
    op.drop_column('reading_progress', 'last_viewed_pages')
    op.drop_column('reading_progress', 'epub_location')
    op.drop_column('reading_progress', 'chapter_href')
    op.drop_column('reading_progress', 'chapter_title')
    op.drop_column('reading_progress', 'viewport_y')
    op.drop_column('reading_progress', 'viewport_x')
    op.drop_column('reading_progress', 'zoom_level')
    op.drop_column('reading_progress', 'scale')
    op.drop_column('reading_progress', 'reading_mode')
    op.drop_column('reading_progress', 'book_format')
