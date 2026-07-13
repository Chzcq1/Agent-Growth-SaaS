"""add founder feedback (outcome/note) to office_runs

Lets the founder mark any run's output as accepted/rejected with an
optional note -- not just Sales Assistant drafts (which already had
PendingApproval/AgentFeedback). This is the raw signal the founder wants to
feed back in continuously (customer accepted vs declined) so the system's
own self-improvement note (see supervisor._recent_feedback_note) can widen
beyond sales_assistant tone to cover any agent's output.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("office_runs", sa.Column("outcome", sa.String(50)))
    op.add_column("office_runs", sa.Column("founder_note", sa.Text))


def downgrade() -> None:
    op.drop_column("office_runs", "founder_note")
    op.drop_column("office_runs", "outcome")
