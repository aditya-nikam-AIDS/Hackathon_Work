from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    complaint_text: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_tier: Mapped[str] = mapped_column(String(30), default="standard", nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(80), nullable=False)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    classification_source: Mapped[str] = mapped_column(String(50), default="fallback", nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_reason: Mapped[str] = mapped_column(Text, nullable=False)
    team: Mapped[str] = mapped_column(String(80), nullable=False)

    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


Index("ix_tickets_priority_status", Ticket.priority, Ticket.status)
Index("ix_tickets_team_status", Ticket.team, Ticket.status)
Index("ix_tickets_category", Ticket.category)
Index("ix_tickets_sla_deadline", Ticket.sla_deadline)
Index("ix_tickets_created_at", Ticket.created_at)

