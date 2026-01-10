"""Safety flags table migration.

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create safety_flags table
    op.create_table(
        'safety_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content_type', sa.String(20), nullable=False),
        sa.Column('content_preview', sa.String(500), nullable=True),
        sa.Column('categories', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('scores', postgresql.JSONB(), nullable=True),
        sa.Column('action_taken', sa.String(30), nullable=False),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Constraints
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "content_type IN ('input', 'output')",
            name='check_content_type'
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name='check_severity'
        ),
        sa.CheckConstraint(
            "action_taken IN ('allowed', 'warned', 'blocked', 'flagged_for_review')",
            name='check_action_taken'
        ),
    )

    # Indexes for safety_flags table
    op.create_index(
        'idx_safety_flags_user_created',
        'safety_flags',
        ['user_id', sa.text('created_at DESC')]
    )
    op.create_index(
        'idx_safety_flags_severity',
        'safety_flags',
        ['severity'],
        postgresql_where=sa.text("severity IN ('high', 'critical')")
    )
    op.create_index(
        'idx_safety_flags_action',
        'safety_flags',
        ['action_taken'],
        postgresql_where=sa.text("action_taken = 'flagged_for_review'")
    )


def downgrade() -> None:
    op.drop_table('safety_flags')
