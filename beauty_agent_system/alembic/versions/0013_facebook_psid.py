"""Add facebook_psid to leads so Messenger DM threads can be linked to a lead

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # facebook_psid: the customer's Page-Scoped ID for a Messenger conversation,
    # used to find-or-create the Lead for an incoming DM and to send replies.
    op.add_column(
        "leads",
        sa.Column("facebook_psid", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_leads_facebook_psid",
        "leads",
        ["facebook_psid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_facebook_psid", table_name="leads")
    op.drop_column("leads", "facebook_psid")
