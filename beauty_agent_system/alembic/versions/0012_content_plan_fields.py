"""Add content_plan, content_ideas, target_profile, pitch_timing, product_pitch to office_runs

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("office_runs", sa.Column("content_plan", sa.JSON(), nullable=True))
    op.add_column("office_runs", sa.Column("content_ideas", sa.JSON(), nullable=True))
    op.add_column("office_runs", sa.Column("target_profile", sa.Text(), nullable=True))
    op.add_column("office_runs", sa.Column("pitch_timing", sa.Text(), nullable=True))
    op.add_column("office_runs", sa.Column("product_pitch", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("office_runs", "product_pitch")
    op.drop_column("office_runs", "pitch_timing")
    op.drop_column("office_runs", "target_profile")
    op.drop_column("office_runs", "content_ideas")
    op.drop_column("office_runs", "content_plan")
