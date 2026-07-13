"""planner agent tables: tasks, daily_updates, daily_briefings

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Do not pre-create this type separately -- see 0001's note on the same
# pitfall with lead_status: op.create_table() creates the enum type as part
# of the column, and a separate .create() call double-creates it.
task_status = sa.Enum("Open", "Done", name="task_status")


def upgrade() -> None:
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

    op.create_table(
        "daily_briefings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("tasks_due_count", sa.Integer, server_default="0"),
        sa.Column("tasks_overdue_count", sa.Integer, server_default="0"),
        sa.Column("new_findings_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("daily_briefings")
    op.drop_table("tasks")
    op.drop_table("daily_updates")
    task_status.drop(op.get_bind(), checkfirst=True)
