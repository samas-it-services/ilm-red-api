"""add_reading_progress

Revision ID: e042ea7f0764
Revises: 0007
Create Date: 2026-01-12 08:19:34.831909+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e042ea7f0764'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create reading_progress table
    op.create_table(
        'reading_progress',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.UUID(), nullable=False),
        sa.Column('current_page', sa.Integer(), nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reading_time_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'book_id', name='uq_progress_user_book'),
        sa.CheckConstraint('current_page >= 1', name='check_current_page_positive'),
        sa.CheckConstraint('total_pages >= 1', name='check_total_pages_positive'),
        sa.CheckConstraint('progress_percent >= 0 AND progress_percent <= 100', name='check_progress_percent_range'),
        sa.CheckConstraint('reading_time_seconds >= 0', name='check_reading_time_positive'),
    )

    # Create indexes for performance
    op.create_index('idx_reading_progress_user_id', 'reading_progress', ['user_id'])
    op.create_index('idx_reading_progress_user_last_read', 'reading_progress', ['user_id', 'last_read_at'])
    op.create_index('idx_reading_progress_book_id', 'reading_progress', ['book_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_reading_progress_book_id', table_name='reading_progress')
    op.drop_index('idx_reading_progress_user_last_read', table_name='reading_progress')
    op.drop_index('idx_reading_progress_user_id', table_name='reading_progress')

    # Drop table
    op.drop_table('reading_progress')
