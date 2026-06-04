"""Add conversation memory: virtual_keys columns + conversations tables.

Revision ID: 007a
Revises: 006a
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "007a"
down_revision = "006a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Memory config on virtual_keys. Default OFF so existing keys are unaffected.
    op.add_column(
        "virtual_keys",
        sa.Column("memory_mode", sa.String(10), nullable=False, server_default="off"),
    )
    op.add_column(
        "virtual_keys",
        sa.Column(
            "memory_max_messages", sa.Integer, nullable=False, server_default="50"
        ),
    )
    op.add_column(
        "virtual_keys",
        sa.Column(
            "memory_max_context_tokens",
            sa.Integer,
            nullable=False,
            server_default="8000",
        ),
    )
    op.add_column(
        "virtual_keys",
        sa.Column(
            "memory_ttl_hours", sa.Integer, nullable=False, server_default="720"
        ),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column(
            "virtual_key_id",
            sa.String(36),
            sa.ForeignKey("virtual_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "is_archived", sa.Boolean, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_conversations_vk_id", "conversations", ["virtual_key_id"])
    op.create_index("idx_conversations_user_id", "conversations", ["user_id"])
    op.create_index("idx_conversations_expires_at", "conversations", ["expires_at"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_conversation_messages_conv_id",
        "conversation_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_conversation_messages_conv_id", table_name="conversation_messages"
    )
    op.drop_table("conversation_messages")
    op.drop_index("idx_conversations_expires_at", table_name="conversations")
    op.drop_index("idx_conversations_user_id", table_name="conversations")
    op.drop_index("idx_conversations_vk_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_column("virtual_keys", "memory_ttl_hours")
    op.drop_column("virtual_keys", "memory_max_context_tokens")
    op.drop_column("virtual_keys", "memory_max_messages")
    op.drop_column("virtual_keys", "memory_mode")
