"""add_rating_flags

Revision ID: d235eb0c7902
Revises: e042ea7f0764
Create Date: 2026-01-12 08:37:20.006228+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd235eb0c7902'
down_revision: Union[str, None] = 'e042ea7f0764'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create rating_flags table
    op.create_table(
        'rating_flags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rating_id', sa.UUID(), nullable=False),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.UUID(), nullable=True),

        sa.ForeignKeyConstraint(['rating_id'], ['ratings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rating_id', 'reporter_id', name='uq_flag_rating_reporter'),
        sa.CheckConstraint(
            "reason IN ('spam', 'offensive', 'irrelevant', 'other')",
            name='check_flag_reason'
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'reviewed', 'dismissed')",
            name='check_flag_status'
        ),
    )

    # Create indexes
    op.create_index('idx_rating_flags_rating_id', 'rating_flags', ['rating_id'])
    op.create_index('idx_rating_flags_status', 'rating_flags', ['status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_rating_flags_status', table_name='rating_flags')
    op.drop_index('idx_rating_flags_rating_id', table_name='rating_flags')

    # Drop table
    op.drop_table('rating_flags')
