from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.tickets import ComplaintCreate, DashboardResponse, TicketResponse
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

