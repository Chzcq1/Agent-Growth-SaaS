"""add plan_trace/review_trace to office_runs

Makes the Supervisor's coordination visible instead of implicit: the
shared goal + per-agent task assignment (plan_trace), and the QA pass that
checks the team's draft for gaps/redundancy before the founder sees it
(review_trace) -- previously the founder only saw parallel, sometimes
redundant, per-agent findings with no visible plan or review step.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("office_runs", sa.Column("plan_trace", sa.JSON))
    op.add_column("office_runs", sa.Column("review_trace", sa.JSON))


def downgrade() -> None:
    op.drop_column("office_runs", "review_trace")
    op.drop_column("office_runs", "plan_trace")
