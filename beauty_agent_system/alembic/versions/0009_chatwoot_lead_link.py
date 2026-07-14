"""link leads to Chatwoot conversations and contacts

Adds chatwoot_conversation_id and chatwoot_contact_id to the leads table so
the AI inbox (Task #6) can look up the right Lead record when a webhook
arrives, and so the sidebar live-feed knows which shop each conversation
belongs to.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("chatwoot_conversation_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("chatwoot_contact_id", sa.String(100), nullable=True),
    )
    # Index for fast webhook-time lookup
    op.create_index(
        "ix_leads_chatwoot_conversation_id",
        "leads",
        ["chatwoot_conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_leads_chatwoot_conversation_id", table_name="leads")
    op.drop_column("leads", "chatwoot_contact_id")
    op.drop_column("leads", "chatwoot_conversation_id")
