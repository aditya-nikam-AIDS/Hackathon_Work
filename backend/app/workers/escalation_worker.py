import time

from backend.app.core.config import get_settings
from backend.app.db.session import SessionLocal, init_db
from backend.app.services.ticket_service import ticket_service


def run_forever() -> None:
    settings = get_settings()
    init_db()
    while True:
        with SessionLocal() as db:
            updated = ticket_service.mark_breached_tickets(db)
            if updated:
                print(f"Escalated {updated} breached tickets.")
        time.sleep(settings.sla_poll_seconds)


if __name__ == "__main__":
    run_forever()

