"""add_quote_tables

Revision ID: 6da4b5c6d7e8
Revises: 5cf3a4b5c6d7
Create Date: 2026-02-12 17:12:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6da4b5c6d7e8'
down_revision: Union[str, None] = '5cf3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. quotes
    op.create_table(
        'quotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('author', sa.String(200), nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_date', sa.Date(), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_quotes_is_active', 'quotes', ['is_active'])
    op.create_index('idx_quotes_is_featured', 'quotes', ['is_featured'])
    op.create_index('idx_quotes_display_date', 'quotes', ['display_date'])
    op.create_index('idx_quotes_category', 'quotes', ['category'])

    # 2. quote_views
    op.create_table(
        'quote_views',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quote_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_quote_views_quote_id', 'quote_views', ['quote_id'])
    op.create_index('idx_quote_views_viewed_at', 'quote_views', ['viewed_at'])


def downgrade() -> None:
    op.drop_index('idx_quote_views_viewed_at', table_name='quote_views')
    op.drop_index('idx_quote_views_quote_id', table_name='quote_views')
    op.drop_table('quote_views')
    op.drop_index('idx_quotes_category', table_name='quotes')
    op.drop_index('idx_quotes_display_date', table_name='quotes')
    op.drop_index('idx_quotes_is_featured', table_name='quotes')
    op.drop_index('idx_quotes_is_active', table_name='quotes')
    op.drop_table('quotes')
