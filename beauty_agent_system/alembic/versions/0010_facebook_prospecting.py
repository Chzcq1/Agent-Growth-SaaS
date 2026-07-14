"""Add source and facebook_comment_id to leads for Facebook prospecting

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # source: where this lead came from (None = manually created, "facebook_comment", etc.)
    op.add_column(
        "leads",
        sa.Column("source", sa.String(50), nullable=True),
    )
    # facebook_comment_id: the comment that triggered the outbound DM / reply
    op.add_column(
        "leads",
        sa.Column("facebook_comment_id", sa.String(200), nullable=True),
    )
    # Index for fast prospecting-log queries
    op.create_index(
        "ix_leads_source",
        "leads",
        ["source"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_source", table_name="leads")
    op.drop_column("leads", "facebook_comment_id")
    op.drop_column("leads", "source")
