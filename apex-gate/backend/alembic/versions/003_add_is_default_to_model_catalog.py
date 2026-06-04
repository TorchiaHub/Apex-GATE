"""Add is_default to model_catalog and update unique constraint.

Revision ID: 003a
Revises: 001a
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "003a"
down_revision = "001a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_default column with server default FALSE (backward compatible).
    # Uses batch_alter_table for SQLite compatibility (SQLite cannot ALTER constraints inline).
    with op.batch_alter_table("model_catalog") as batch_op:
        batch_op.add_column(
            sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false())
        )
        # Replace the old single-column UNIQUE on model_id with a composite
        # UNIQUE on (provider_id, model_id) that allows the same model_id
        # to appear for different providers.
        batch_op.drop_constraint("uq_model_catalog_model_id", type_="unique")
        batch_op.create_unique_constraint(
            "uq_model_catalog_provider_model", ["provider_id", "model_id"]
        )

    # Composite index for fast default-model lookup per provider (AUTO mode).
    op.create_index(
        "ix_model_catalog_default", "model_catalog", ["provider_id", "is_default"]
    )


def downgrade() -> None:
    op.drop_index("ix_model_catalog_default", table_name="model_catalog")

    with op.batch_alter_table("model_catalog") as batch_op:
        batch_op.drop_constraint("uq_model_catalog_provider_model", type_="unique")
        batch_op.create_unique_constraint("uq_model_catalog_model_id", ["model_id"])
        batch_op.drop_column("is_default")
