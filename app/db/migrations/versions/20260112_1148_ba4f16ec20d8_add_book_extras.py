"""add_book_extras

Revision ID: ba4f16ec20d8
Revises: d235eb0c7902
Create Date: 2026-01-12 11:48:05.788802+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba4f16ec20d8'
down_revision: Union[str, None] = 'd235eb0c7902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create book_extras table
    op.create_table(
        'book_extras',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('url', sa.String(500), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(20), server_default='published', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_id', 'type', 'title', name='uq_book_extra_type_title'),
        sa.CheckConstraint(
            "type IN ('flashcard', 'quiz', 'audio', 'podcast', 'video', 'infographic', 'simple_explanation', 'key_ideas')",
            name='check_book_extra_type'
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name='check_book_extra_status'
        ),
    )

    # Create indexes
    op.create_index('idx_book_extras_book_id', 'book_extras', ['book_id'])
    op.create_index('idx_book_extras_type', 'book_extras', ['type'])
    op.create_index('idx_book_extras_status', 'book_extras', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_book_extras_status', table_name='book_extras')
    op.drop_index('idx_book_extras_type', table_name='book_extras')
    op.drop_index('idx_book_extras_book_id', table_name='book_extras')

    # Drop table
    op.drop_table('book_extras')
