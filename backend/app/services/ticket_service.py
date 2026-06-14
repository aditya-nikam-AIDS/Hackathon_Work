import json
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Ticket
from backend.app.schemas.tickets import ComplaintCreate, DashboardResponse, TicketResponse
from backend.app.services.nlp.classifier import ComplaintClassifier
from backend.app.services.priority_engine import PriorityEngine
from backend.app.services.routing_engine import RoutingEngine
from backend.app.services.sla_engine import SLAEngine


class TicketService:
    def __init__(self):
        settings = get_settings()
        self.classifier = ComplaintClassifier(settings)
        self.priority_engine = PriorityEngine()
        self.routing_engine = RoutingEngine()
        self.sla_engine = SLAEngine()

    async def create_ticket(self, db: Session, payload: ComplaintCreate) -> TicketResponse:
        created_at = datetime.now(timezone.utc)
        classification = await self.classifier.classify(payload.complaint_text)
        priority_decision = self.priority_engine.decide(
            text=payload.complaint_text,
            category=classification.category,
            sentiment_score=classification.sentiment_score,
            customer_tier=payload.customer_tier,
        )
        routing_decision = self.routing_engine.route(
            category=classification.category,
            priority=priority_decision.priority,
            customer_tier=payload.customer_tier,
        )
        sla_deadline = self.sla_engine.deadline_for(created_at=created_at, priority=priority_decision.priority)

        ticket = Ticket(
            id=str(uuid4()),
            complaint_text=payload.complaint_text,
            customer_id=payload.customer_id,
            customer_tier=payload.customer_tier,
            metadata_json=json.dumps(payload.metadata),
            category=classification.category,
            classification_confidence=classification.confidence,
            classification_source=classification.source,
            sentiment_score=classification.sentiment_score,
            priority=priority_decision.priority,
            priority_reason=priority_decision.reason,
            team=routing_decision.team,
            status="open",
            sla_deadline=sla_deadline,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return self.to_response(ticket)

    def list_tickets(
        self,
        db: Session,
        *,
        priority: str | None = None,
        team: str | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[TicketResponse]:
        self.mark_breached_tickets(db)

        statement = select(Ticket).order_by(Ticket.created_at.desc()).limit(limit)
        if priority:
            statement = statement.where(Ticket.priority == priority)
        if team:
            statement = statement.where(Ticket.team == team)
        if status:
            statement = statement.where(Ticket.status == status)
        if category:
            statement = statement.where(Ticket.category == category)

        tickets = db.execute(statement).scalars().all()
        return [self.to_response(ticket) for ticket in tickets]

    def dashboard(self, db: Session) -> DashboardResponse:
        self.mark_breached_tickets(db)
        tickets = db.execute(select(Ticket).order_by(Ticket.created_at.desc()).limit(250)).scalars().all()
        responses = [self.to_response(ticket) for ticket in tickets]

        by_priority = Counter(ticket.priority for ticket in tickets)
        by_team = Counter(ticket.team for ticket in tickets)
        by_category = Counter(ticket.category for ticket in tickets)

        breached = [ticket for ticket in responses if ticket.sla_state == "breached"]
        due_soon = [ticket for ticket in responses if ticket.sla_state == "due_soon"]
        alerts = sorted(
            breached + due_soon,
            key=lambda ticket: ticket.sla_remaining_seconds,
        )[:20]

        return DashboardResponse(
            total_tickets=len(responses),
            open_tickets=sum(1 for ticket in responses if ticket.status in {"open", "in_progress"}),
            breached_tickets=len(breached),
            due_soon_tickets=len(due_soon),
            escalated_tickets=sum(1 for ticket in tickets if ticket.escalated_at is not None),
            by_priority=dict(by_priority),
            by_team=dict(by_team),
            by_category=dict(by_category),
            alerts=alerts,
            tickets=responses,
        )

    def mark_breached_tickets(self, db: Session) -> int:
        open_tickets = db.execute(
            select(Ticket).where(Ticket.status.in_(["open", "in_progress"]), Ticket.escalated_at.is_(None))
        ).scalars()
        now = datetime.now(timezone.utc)
        updated = 0
        for ticket in open_tickets:
            sla_status = self.sla_engine.status_for(deadline=ticket.sla_deadline, ticket_status=ticket.status, now=now)
            if sla_status.should_escalate:
                ticket.escalated_at = now
                ticket.updated_at = now
                updated += 1
        if updated:
            db.commit()
        return updated

    def to_response(self, ticket: Ticket) -> TicketResponse:
        sla_status = self.sla_engine.status_for(deadline=ticket.sla_deadline, ticket_status=ticket.status)
        metadata = {}
        if ticket.metadata_json:
            try:
                metadata = json.loads(ticket.metadata_json)
            except json.JSONDecodeError:
                metadata = {}

        return TicketResponse(
            id=ticket.id,
            complaint_text=ticket.complaint_text,
            customer_id=ticket.customer_id,
            customer_tier=ticket.customer_tier,
            metadata=metadata,
            category=ticket.category,
            classification_confidence=round(ticket.classification_confidence, 3),
            classification_source=ticket.classification_source,
            sentiment_score=round(ticket.sentiment_score, 3),
            priority=ticket.priority,
            priority_reason=ticket.priority_reason,
            team=ticket.team,
            status=ticket.status,
            sla_deadline=ticket.sla_deadline,
            sla_remaining_seconds=sla_status.remaining_seconds,
            sla_state=sla_status.state,
            escalated_at=ticket.escalated_at,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
        )


ticket_service = TicketService()
