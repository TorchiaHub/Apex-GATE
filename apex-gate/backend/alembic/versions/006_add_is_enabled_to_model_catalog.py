"""Add is_enabled (user curation) to model_catalog.

Revision ID: 006a
Revises: 005a
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "006a"
down_revision = "005a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_catalog",
        sa.Column(
            "is_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("model_catalog", "is_enabled")
