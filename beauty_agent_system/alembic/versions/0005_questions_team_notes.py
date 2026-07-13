"""add questions/team_notes to office_runs

Lets a worker agent say "I don't have enough to answer confidently" as an
actual, specific clarifying question shown to the founder (instead of a
passive missing_info bullet), and lets any agent surface a proactive idea
or signal it noticed outside its own narrow task (team_notes) -- the
"think for yourself, ask when unsure, mention ideas you notice" behavior
the founder asked for.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("office_runs", sa.Column("questions", sa.JSON))
    op.add_column("office_runs", sa.Column("team_notes", sa.JSON))


def downgrade() -> None:
    op.drop_column("office_runs", "team_notes")
    op.drop_column("office_runs", "questions")
