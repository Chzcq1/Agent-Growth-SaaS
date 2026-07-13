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


class KbArticle(Base):
    """Knowledge Base article used by Agent 3 (Support) for RAG-only answers."""

    __tablename__ = "kb_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SupportTicket(Base):
    """Escalation created when Agent 3 has no confident KB answer."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_id: Mapped[int | None] = mapped_column(ForeignKey("leads.shop_id"))
    question: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WeeklyInsight(Base):
    """Self-improvement summary produced from agent_feedback, weekly."""

    __tablename__ = "weekly_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    week_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    applied: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TaskStatus(str, enum.Enum):
    OPEN = "Open"
    DONE = "Done"


class Task(Base):
    """A concrete to-do for the founder, either created by hand or by the
    Planner agent while triaging a DailyUpdate. Always carries a deadline
    (``due_date``) so the daily briefing can flag overdue work."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(50))  # sales/support/marketing/other
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=TaskStatus.OPEN,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    source_update_id: Mapped[int | None] = mapped_column(ForeignKey("daily_updates.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class DailyUpdate(Base):
    """A free-text note the founder logs about anything that happened --
    a customer message, a competitor move, a market observation. The
    Planner agent (Agent 5) triages it into a summary, an optional suggested
    reply, and an optional Task with a deadline."""

    __tablename__ = "daily_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    update_type: Mapped[str | None] = mapped_column(String(50))
    summary: Mapped[str | None] = mapped_column(Text)
    needs_reply: Mapped[bool] = mapped_column(default=False)
    suggested_reply: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DailyBriefing(Base):
    """A generated daily digest: what's due today/overdue, and what's new.
    Stored so the founder can look back at past days, not just today's."""

    __tablename__ = "daily_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    tasks_due_count: Mapped[int] = mapped_column(Integer, default=0)
    tasks_overdue_count: Mapped[int] = mapped_column(Integer, default=0)
    new_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SystemState(Base):
    """Small key/value store for bot sleep-mode + misc runtime flags."""

    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
