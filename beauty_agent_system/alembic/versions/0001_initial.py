"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Do not pre-create this type separately: op.create_table() below already
# creates the Postgres ENUM type as part of creating the "leads" column, and
# calling .create() a second time raises "type already exists".
lead_status = sa.Enum(
    "New", "Contacted", "FollowUp_1", "FollowUp_2", "Trial", "Ghosted", "Blocked",
    name="lead_status",
)


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("shop_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("shop_name", sa.String(255), nullable=False),
        sa.Column("facebook_url", sa.String(500)),
        sa.Column("line_id", sa.String(255)),
        sa.Column("status", lead_status, server_default="New"),
        sa.Column("pain_points", sa.JSON),
        sa.Column("last_contacted_date", sa.DateTime),
        sa.Column("next_followup_date", sa.DateTime),
        sa.Column("conversation_history", sa.JSON, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "api_usage_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("model_used", sa.String(100)),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("status", sa.String(50)),
        sa.Column("detail", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "pending_approvals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("leads.shop_id")),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("draft_message", sa.Text),
        sa.Column("reasoning", sa.Text),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime),
    )

    op.create_table(
        "agent_feedback",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("approval_id", sa.Integer, sa.ForeignKey("pending_approvals.id")),
        sa.Column("outcome", sa.String(50)),
        sa.Column("founder_note", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "research_cache",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("query_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("query_text", sa.Text),
        sa.Column("result", sa.JSON),
        sa.Column("verified", sa.Boolean, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "kb_articles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("tags", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("leads.shop_id")),
        sa.Column("question", sa.Text),
        sa.Column("summary", sa.Text),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "weekly_insights",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.DateTime, nullable=False),
        sa.Column("summary_text", sa.Text),
        sa.Column("recommendation", sa.Text),
        sa.Column("applied", sa.Boolean, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "system_state",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.JSON),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("system_state")
    op.drop_table("weekly_insights")
    op.drop_table("support_tickets")
    op.drop_table("kb_articles")
    op.drop_table("research_cache")
    op.drop_table("agent_feedback")
    op.drop_table("pending_approvals")
    op.drop_table("api_usage_log")
    op.drop_table("leads")
    lead_status.drop(op.get_bind(), checkfirst=True)
