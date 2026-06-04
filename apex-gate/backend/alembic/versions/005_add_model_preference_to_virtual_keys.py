"""Add model_preference column to virtual_keys.

Revision ID: 005a
Revises: 004a
Create Date: 2026-05-30
"""

from alembic import op
import sqlalchemy as sa

revision = "005a"
down_revision = "004a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "virtual_keys",
        sa.Column("model_preference", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("virtual_keys", "model_preference")
