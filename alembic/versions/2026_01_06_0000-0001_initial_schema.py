"""Initial schema with all tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("ric_address", sa.String(length=20), nullable=False, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_pagers_ric", "pagers", ["ric_address"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("frequency", sa.Float(), nullable=False),
        sa.Column("baud_rate", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_messages_timestamp",
        "messages",
        ["timestamp"],
        unique=False,
        postgresql_ops={"timestamp": "DESC"},
    )
    op.create_index("idx_messages_status", "messages", ["status"], unique=False)

    op.create_table(
        "message_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pager_id", sa.Integer(), sa.ForeignKey("pagers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ric_address", sa.String(length=20), nullable=False),
    )
    op.create_index("idx_recipients_message", "message_recipients", ["message_id"], unique=False)
    op.create_index("idx_recipients_pager", "message_recipients", ["pager_id"], unique=False)

    op.create_table(
        "system_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_config_key", "system_config", ["key"], unique=True)

    op.create_table(
        "transmission_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_logs_timestamp",
        "transmission_logs",
        ["timestamp"],
        unique=False,
        postgresql_ops={"timestamp": "DESC"},
    )
    op.create_index("idx_logs_message", "transmission_logs", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_logs_message", table_name="transmission_logs")
    op.drop_index("idx_logs_timestamp", table_name="transmission_logs")
    op.drop_table("transmission_logs")

    op.drop_index("idx_config_key", table_name="system_config")
    op.drop_table("system_config")

    op.drop_index("idx_recipients_pager", table_name="message_recipients")
    op.drop_index("idx_recipients_message", table_name="message_recipients")
    op.drop_table("message_recipients")

    op.drop_index("idx_messages_status", table_name="messages")
    op.drop_index("idx_messages_timestamp", table_name="messages")
    op.drop_table("messages")

    op.drop_index("idx_pagers_ric", table_name="pagers")
    op.drop_table("pagers")
