"""Add extra_data JSONB column to users table for flexible profile fields.

Revision ID: 20260110_0007
Revises: 20260109_0006_pages_chunks
Create Date: 2026-01-10

This migration adds a future-proof JSONB column for storing additional user
profile fields without requiring schema changes. Fields like full_name, city,
state_province, country, date_of_birth can be stored here.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic
revision = "20260110_0007"
down_revision = "20260109_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add extra_data column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "extra_data",
            JSONB,
            nullable=True,
            server_default="{}",
            comment="Flexible JSON storage for extended profile fields (full_name, city, country, etc.)",
        ),
    )


def downgrade() -> None:
    """Remove extra_data column from users table."""
    op.drop_column("users", "extra_data")
