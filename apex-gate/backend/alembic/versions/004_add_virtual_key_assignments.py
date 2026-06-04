"""Add virtual_key_assignments table.

Revision ID: 004a
Revises: 003a
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "004a"
down_revision = "003a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "virtual_key_assignments",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("vk_id", sa.String(36), sa.ForeignKey("virtual_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
        sa.UniqueConstraint("vk_id", "api_key_id", name="uq_vka_vk_api_key"),
    )
    op.create_index("ix_vka_vk_id", "virtual_key_assignments", ["vk_id"])
    op.create_index("ix_vka_api_key_id", "virtual_key_assignments", ["api_key_id"])


def downgrade() -> None:
    op.drop_index("ix_vka_api_key_id", table_name="virtual_key_assignments")
    op.drop_index("ix_vka_vk_id", table_name="virtual_key_assignments")
    op.drop_table("virtual_key_assignments")
