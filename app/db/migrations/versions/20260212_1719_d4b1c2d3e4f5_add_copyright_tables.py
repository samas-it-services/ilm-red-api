"""add_copyright_tables

Revision ID: d4b1c2d3e4f5
Revises: c3a0b1c2d3e4
Create Date: 2026-02-12 17:19:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4b1c2d3e4f5'
down_revision: Union[str, None] = 'c3a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'book_discovery_rewards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('isbn', sa.String(20), nullable=True),
        sa.Column('copyright_status', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('legal_declaration', sa.Text(), nullable=True),
        sa.Column('passage_content', sa.Text(), nullable=True),
        sa.Column('suggestion_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('points_awarded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discovery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_discovery_rewards_book', 'book_discovery_rewards', ['book_id'])
    op.create_index('idx_book_discovery_rewards_user', 'book_discovery_rewards', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_book_discovery_rewards_user', table_name='book_discovery_rewards')
    op.drop_index('idx_book_discovery_rewards_book', table_name='book_discovery_rewards')
    op.drop_table('book_discovery_rewards')
