"""Add tiktok_comment_id and tiktok_video_id to leads for TikTok prospecting

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("tiktok_comment_id", sa.String(200), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("tiktok_video_id", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_leads_tiktok_comment_id",
        "leads",
        ["tiktok_comment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_tiktok_comment_id", table_name="leads")
    op.drop_column("leads", "tiktok_video_id")
    op.drop_column("leads", "tiktok_comment_id")
