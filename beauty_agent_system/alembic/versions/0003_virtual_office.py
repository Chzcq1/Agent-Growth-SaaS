"""virtual office rebuild: drop kb/support/planner tables, add office_runs

The Founder-facing product changed from a multi-page admin dashboard (with
a separate Support/KB system and a Planner-driven Updates/Tasks/Daily
Briefing flow) to a single-page "Virtual Office": one raw-text input,
routed by the Supervisor to whichever of 6 specialist agents are relevant,
synthesized into one Key Findings + Action Plan answer. leads,
pending_approvals, agent_feedback, research_cache, api_usage_log are
untouched (still the backbone: leads/approvals/feedback/rate-limit log).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

task_status = sa.Enum("Open", "Done", name="task_status")


def upgrade() -> None:
    op.drop_table("tasks")
    task_status.drop(op.get_bind(), checkfirst=True)
    op.drop_table("daily_updates")
    op.drop_table("daily_briefings")
    op.drop_table("weekly_insights")
    op.drop_table("support_tickets")
    op.drop_table("kb_articles")

    op.create_table(
        "office_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("agents_run", sa.JSON, server_default="[]"),
        sa.Column("key_findings", sa.JSON, server_default="[]"),
        sa.Column("founder_actions", sa.JSON, server_default="[]"),
        sa.Column("ai_actions", sa.JSON, server_default="[]"),
        sa.Column("missing_info", sa.JSON, server_default="[]"),
        sa.Column("approval_id", sa.Integer, sa.ForeignKey("pending_approvals.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("office_runs")

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
        "daily_updates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("update_type", sa.String(50)),
        sa.Column("summary", sa.Text),
        sa.Column("needs_reply", sa.Boolean, server_default=sa.false()),
        sa.Column("suggested_reply", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "daily_briefings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("tasks_due_count", sa.Integer, server_default="0"),
        sa.Column("tasks_overdue_count", sa.Integer, server_default="0"),
        sa.Column("new_findings_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(50)),
        sa.Column("status", task_status, server_default="Open"),
        sa.Column("due_date", sa.DateTime),
        sa.Column("source_update_id", sa.Integer, sa.ForeignKey("daily_updates.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
    )
