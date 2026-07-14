"""add stage and last_contacted_at to leads table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use VARCHAR so we don't need a native Postgres ENUM type --
    # SQLAlchemy validates enum membership on the Python side.
    op.add_column(
        "leads",
        sa.Column("stage", sa.String(50), server_default="cold", nullable=False),
    )
    op.add_column(
        "leads",
        sa.Column("last_contacted_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "last_contacted_at")
    op.drop_column("leads", "stage")
