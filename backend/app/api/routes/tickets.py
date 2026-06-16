from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.tickets import ComplaintCreate, DashboardResponse, TicketResponse
from backend.app.services.optimizer import BANKING_TICKET_TEMPLATES, performance_metrics
from backend.app.services.ticket_service import ticket_service

router = APIRouter(tags=["tickets"])


@router.post("/create-ticket", response_model=TicketResponse, status_code=201)
async def create_ticket(payload: ComplaintCreate, db: Session = Depends(get_db)) -> TicketResponse:
    return await ticket_service.create_ticket(db, payload)


@router.get("/tickets", response_model=list[TicketResponse])
def get_tickets(
    priority: str | None = None,
    team: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TicketResponse]:
    return ticket_service.list_tickets(
        db,
        priority=priority,
        team=team,
        status=status,
        category=category,
        limit=limit,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return ticket_service.dashboard(db)


@router.post("/run-escalations")
def run_escalations(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"escalated": ticket_service.mark_breached_tickets(db)}


@router.get("/templates")
def get_ticket_templates() -> dict:
    """Get banking ticket templates for quick ticket creation."""
    return {
        "templates": BANKING_TICKET_TEMPLATES,
        "count": len(BANKING_TICKET_TEMPLATES),
    }


@router.get("/metrics")
def get_performance_metrics() -> dict:
    """Get system performance metrics."""
    return performance_metrics.to_dict()


@router.post("/tickets/{ticket_id}/feedback")
def submit_ticket_feedback(
    ticket_id: str,
    correct_category: str | None = None,
    correct_priority: str | None = None,
    agent_notes: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Submit agent feedback for a ticket to improve classification accuracy."""
    # This would typically update a feedback table for retraining
    # For now, just acknowledge the feedback
    feedback_data = {
        "ticket_id": ticket_id,
        "correct_category": correct_category,
        "correct_priority": correct_priority,
        "agent_notes": agent_notes,
    }
    # In production: store in feedback table, trigger retraining pipeline
    _ = db  # Acknowledge db parameter
    return {
        "ticket_id": ticket_id,
        "feedback_received": True,
        "feedback_data": feedback_data,
        "message": "Thank you! This feedback will help improve classification accuracy.",
    }


@router.get("/workload")
def get_team_workload(db: Session = Depends(get_db)) -> dict:
    """Get current team workload for load balancing."""
    from backend.app.services.optimizer import ticket_optimizer
    return ticket_optimizer.get_workload_balance(db)

