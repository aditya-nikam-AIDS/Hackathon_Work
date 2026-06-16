from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CustomerTier = Literal["vip", "premium", "standard", "trial"]
Priority = Literal["critical", "high", "medium", "low"]
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
ClassificationMode = Literal["auto", "llm", "tfidf"]


class ComplaintCreate(BaseModel):
    complaint_text: str = Field(..., min_length=5, max_length=8000)
    customer_id: str | None = Field(default=None, max_length=120)
    customer_tier: CustomerTier = "standard"
    classification_mode: ClassificationMode = "auto"
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketReroute(BaseModel):
    team: str = Field(..., min_length=2, max_length=80)
    observation: str = Field(..., min_length=5, max_length=1000)
    status: TicketStatus | None = None


class TicketResponse(BaseModel):
    id: str
    complaint_text: str
    customer_id: str | None
    customer_tier: str
    metadata: dict[str, Any]
    category: str
    classification_confidence: float
    classification_source: str
    sentiment_score: float
    priority: str
    priority_reason: str
    team: str
    status: str
    sla_deadline: datetime
    sla_remaining_seconds: int
    sla_state: str
    escalated_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    total_tickets: int
    open_tickets: int
    breached_tickets: int
    due_soon_tickets: int
    escalated_tickets: int
    by_priority: dict[str, int]
    by_team: dict[str, int]
    by_category: dict[str, int]
    alerts: list[TicketResponse]
    tickets: list[TicketResponse]

