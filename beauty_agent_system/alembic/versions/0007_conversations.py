"""add conversations table + link office_runs to it, add image_urls

Lets the founder split the single endless page into separate, deletable
chat threads (sidebar), and lets a message carry attached images. Existing
office_runs rows are backfilled into one "แชทเก่า" conversation so history
isn't orphaned.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-14

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(200), server_default="แชทใหม่"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.add_column("office_runs", sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id")))
    op.add_column("office_runs", sa.Column("image_urls", sa.JSON, server_default="[]"))
    op.add_column("office_runs", sa.Column("general_answer", sa.Text))

    # Backfill: if there is existing history, give it a home conversation so
    # old runs stay visible instead of disappearing from every sidebar thread.
    conn = op.get_bind()
    existing = conn.execute(sa.text("SELECT COUNT(*) FROM office_runs")).scalar()
    if existing:
        conn.execute(
            sa.text("INSERT INTO conversations (title) VALUES ('แชทเก่า')")
        )
        new_id = conn.execute(sa.text("SELECT MAX(id) FROM conversations")).scalar()
        conn.execute(
            sa.text("UPDATE office_runs SET conversation_id = :cid WHERE conversation_id IS NULL"),
            {"cid": new_id},
        )


def downgrade() -> None:
    op.drop_column("office_runs", "general_answer")
    op.drop_column("office_runs", "image_urls")
    op.drop_column("office_runs", "conversation_id")
    op.drop_table("conversations")
