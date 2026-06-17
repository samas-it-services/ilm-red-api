"""add_search_analytics

Revision ID: e5c2d3e4f5a6
Revises: d4b1c2d3e4f5
Create Date: 2026-02-12 17:20:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5c2d3e4f5a6'
down_revision: Union[str, None] = 'd4b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'search_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('search_query', sa.String(500), nullable=False),
        sa.Column('search_type', sa.String(50), nullable=False),
        sa.Column('search_source', sa.String(50), nullable=True),
        sa.Column('filters_used', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('result_count', sa.Integer(), nullable=False),
        sa.Column('results_clicked', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_search_analytics_user_id', 'search_analytics', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_search_analytics_user_id', table_name='search_analytics')
    op.drop_table('search_analytics')
