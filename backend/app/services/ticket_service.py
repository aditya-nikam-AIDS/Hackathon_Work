import json
import time
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import Ticket
from backend.app.schemas.tickets import ComplaintCreate, DashboardResponse, TicketResponse
from backend.app.services.agentic.workflow import ComplaintAgentWorkflow
from backend.app.services.optimizer import performance_metrics, ticket_optimizer
from backend.app.services.sla_engine import SLAEngine


class TicketService:
    def __init__(self):
        settings = get_settings()
        self.agent_workflow = ComplaintAgentWorkflow(settings)
        self.sla_engine = SLAEngine()
        self.optimizer = ticket_optimizer

    async def create_ticket(self, db: Session, payload: ComplaintCreate) -> TicketResponse:
        start_time = time.time()
        created_at = datetime.now(timezone.utc)
        
        # Check for duplicate tickets
        similar_tickets = self.optimizer.find_similar_tickets(
            db, payload.complaint_text, payload.customer_id
        )
        
        if similar_tickets:
            performance_metrics.record_duplicate_detected()
            # Add duplicate warning to metadata
            payload.metadata["duplicate_warning"] = {
                "similar_ticket_ids": [t.id for t in similar_tickets[:3]],
                "similarity_detected": True,
            }
        
        decision = await self.agent_workflow.process(
            complaint_text=payload.complaint_text,
            customer_id=payload.customer_id,
            customer_tier=payload.customer_tier,
            metadata=payload.metadata,
            created_at=created_at,
        )
        classification = decision.classification
        priority_decision = decision.priority_decision
        routing_decision = decision.routing_decision
        
        # Calculate confidence score
        confidence_score = self.optimizer.calculate_confidence_score(
            classification.confidence,
            priority_decision.score,
            len(similar_tickets) > 0,
        )
        
        # Get auto-response suggestion
        auto_response = self.optimizer.suggest_auto_response(
            classification.category, priority_decision.priority
        )
        
        metadata = {
            **payload.metadata,
            "agentic_workflow": {
                "version": decision.workflow_version,
                "requires_human_review": decision.requires_human_review,
                "recommended_actions": decision.recommended_actions,
                "escalation_summary": decision.escalation_summary,
                "trace": decision.agent_trace,
            },
            "optimization": {
                "confidence_score": confidence_score,
                "auto_response": auto_response,
                "processing_time_ms": 0,  # Will update below
            },
        }

        ticket = Ticket(
            id=str(uuid4()),
            complaint_text=payload.complaint_text,
            customer_id=payload.customer_id,
            customer_tier=payload.customer_tier,
            metadata_json=json.dumps(metadata),
            category=classification.category,
            classification_confidence=classification.confidence,
            classification_source=classification.source,
            sentiment_score=classification.sentiment_score,
            priority=priority_decision.priority,
            priority_reason=priority_decision.reason,
            team=routing_decision.team,
            status="open",
            sla_deadline=decision.sla_deadline,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        
        # Record performance metrics
        processing_time = (time.time() - start_time) * 1000
        performance_metrics.record_processing_time(processing_time)
        
        # Update metadata with actual processing time
        metadata["optimization"]["processing_time_ms"] = round(processing_time, 2)
        ticket.metadata_json = json.dumps(metadata)
        db.commit()
        
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
