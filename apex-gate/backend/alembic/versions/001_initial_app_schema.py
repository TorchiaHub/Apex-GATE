"""Initial App DB schema.

Revision ID: 001a
Revises:
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "001a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("api_base_url", sa.String(500), nullable=True),
        sa.Column("supports_free_tier", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("litellm_prefix", sa.String(50), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="99"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_encrypted", sa.Text, nullable=False),
        sa.Column("tier", sa.String(10), nullable=False, server_default="free"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="10"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("rate_limit_rpm", sa.Integer, nullable=True),
        sa.Column("rate_limit_rpd", sa.Integer, nullable=True),
        sa.Column("budget_daily_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("budget_monthly_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_provider_id", "api_keys", ["provider_id"])
    op.create_index("ix_api_keys_user_id_priority", "api_keys", ["user_id", "priority"])

    op.create_table(
        "virtual_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("daily_token_budget", sa.Integer, nullable=True),
        sa.Column("allowed_providers", sa.Text, nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_virtual_keys_user_id", "virtual_keys", ["user_id"])
    op.create_index("idx_virtual_keys_hash", "virtual_keys", ["key_hash"])

    op.create_table(
        "model_catalog",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_id", sa.String(36), sa.ForeignKey("providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("context_window", sa.Integer, nullable=True),
        sa.Column("tier", sa.String(10), nullable=False, server_default="free"),
        sa.Column("cost_input_per_1m_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("cost_output_per_1m_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("supports_vision", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("supports_tools", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("supports_streaming", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_model_catalog_provider", "model_catalog", ["provider_id"])
    op.create_index("idx_model_catalog_tier", "model_catalog", ["tier"])
    op.create_index("idx_model_catalog_active", "model_catalog", ["is_active"])

    op.create_table(
        "request_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("virtual_key_id", sa.String(36), sa.ForeignKey("virtual_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_id", sa.String(200), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("protocol", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_request_logs_user_id", "request_logs", ["user_id"])
    op.create_index("idx_request_logs_created", "request_logs", ["created_at"])
    op.create_index("idx_request_logs_vk", "request_logs", ["virtual_key_id"])
    op.create_index("idx_request_logs_api_key", "request_logs", ["api_key_id"])
    op.create_index("idx_request_logs_status", "request_logs", ["status"])

    op.create_table(
        "exhaustion_state",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("exhausted_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_exhaustion_until", "exhaustion_state", ["exhausted_until"])


def downgrade() -> None:
    op.drop_table("exhaustion_state")
    op.drop_table("request_logs")
    op.drop_table("model_catalog")
    op.drop_table("virtual_keys")
    op.drop_table("api_keys")
    op.drop_table("providers")
