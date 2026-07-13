"""SQLAlchemy ORM models mirroring the schema in README / alembic migration."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeadStatus(str, enum.Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    FOLLOWUP_1 = "FollowUp_1"
    FOLLOWUP_2 = "FollowUp_2"
    TRIAL = "Trial"
    GHOSTED = "Ghosted"
    BLOCKED = "Blocked"


class Lead(Base):
    __tablename__ = "leads"

    shop_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facebook_url: Mapped[str | None] = mapped_column(String(500))
    line_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus,
            name="lead_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=LeadStatus.NEW,
    )
    pain_points: Mapped[dict | None] = mapped_column(JSON)
    last_contacted_date: Mapped[datetime | None] = mapped_column(DateTime)
    next_followup_date: Mapped[datetime | None] = mapped_column(DateTime)
    conversation_history: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    approvals: Mapped[list["PendingApproval"]] = relationship(back_populates="lead")


class ApiUsageLog(Base):
    __tablename__ = "api_usage_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str | None] = mapped_column(String(100))
    model_used: Mapped[str | None] = mapped_column(String(100))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str | None] = mapped_column(String(50))  # success/rate_limited/error
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("leads.shop_id"))
    agent_name: Mapped[str | None] = mapped_column(String(100))
    draft_message: Mapped[str | None] = mapped_column(Text)
    reasoning: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    lead: Mapped["Lead"] = relationship(back_populates="approvals")
    feedback: Mapped[list["AgentFeedback"]] = relationship(back_populates="approval")


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    approval_id: Mapped[int | None] = mapped_column(ForeignKey("pending_approvals.id"))
    outcome: Mapped[str | None] = mapped_column(String(50))  # replied/ignored/converted/blocked
    founder_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    approval: Mapped["PendingApproval"] = relationship(back_populates="feedback")


class ResearchCache(Base):
    __tablename__ = "research_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    query_text: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(JSON)
    verified: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Conversation(Base):
    """A chat thread in the sidebar -- lets the founder split unrelated
    topics (a nail-salon growth question vs. a completely unrelated general
    question) into separate, deletable threads instead of one endless page.
    Title is auto-set from the first message and never edited by an agent."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), default="แชทใหม่")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    runs: Mapped[list["OfficeRun"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class OfficeRun(Base):
    """One founder submission through the Virtual Office: the raw pasted
    text, which agents the Supervisor decided were relevant, and the
    synthesized Key Findings / Action Plan. Kept so a page reload doesn't
    lose the last result and the founder can glance at recent history."""

    __tablename__ = "office_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Relative /static/uploads/... URLs of images the founder attached to this
    # message -- shown as thumbnails in the chat bubble and, when present,
    # passed to the vision-capable General Assistant.
    image_urls: Mapped[list] = mapped_column(JSON, default=list)
    agents_run: Mapped[list] = mapped_column(JSON, default=list)
    # Freeform reply from general_assistant (general/non-CSC question, or an
    # image analysis) -- kept separate from key_findings since it's prose,
    # not a bullet list, and needs its own rendering.
    general_answer: Mapped[str | None] = mapped_column(Text)
    plan_trace: Mapped[dict | None] = mapped_column(JSON)
    review_trace: Mapped[dict | None] = mapped_column(JSON)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    team_notes: Mapped[list] = mapped_column(JSON, default=list)
    key_findings: Mapped[list] = mapped_column(JSON, default=list)
    founder_actions: Mapped[list] = mapped_column(JSON, default=list)
    ai_actions: Mapped[list] = mapped_column(JSON, default=list)
    missing_info: Mapped[list] = mapped_column(JSON, default=list)
    approval_id: Mapped[int | None] = mapped_column(ForeignKey("pending_approvals.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Founder's own reaction to this run's output ("accepted"/"rejected" +
    # optional note) -- the raw signal fed back into future runs so the
    # system improves from real outcomes instead of resetting every time.
    outcome: Mapped[str | None] = mapped_column(String(50))
    founder_note: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped["Conversation"] = relationship(back_populates="runs")


class SystemState(Base):
    """Small key/value store for bot sleep-mode + misc runtime flags."""

    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
