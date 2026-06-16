from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


# Banking domain SLA hours - faster response times required
SLA_HOURS = {
    "critical": 1,    # 1 hour for fraud, security, VIP urgent
    "high": 4,        # 4 hours for payment failures, login issues
    "medium": 12,     # 12 hours for general issues, delays
    "low": 24,        # 24 hours for minor queries, informational
}

# Warning threshold at 15 minutes for banking (faster escalation)
WARNING_THRESHOLD_SECONDS = 15 * 60


@dataclass
class SLAStatus:
    remaining_seconds: int
    state: str
    is_breached: bool
    should_escalate: bool


class SLAEngine:
    def deadline_for(self, *, created_at: datetime, priority: str) -> datetime:
        normalized_created_at = self._ensure_aware(created_at)
        hours = SLA_HOURS.get(priority, SLA_HOURS["low"])
        return normalized_created_at + timedelta(hours=hours)

    def status_for(
        self,
        *,
        deadline: datetime,
        ticket_status: str,
        now: datetime | None = None,
    ) -> SLAStatus:
        now = self._ensure_aware(now or datetime.now(timezone.utc))
        deadline = self._ensure_aware(deadline)

        if ticket_status in {"resolved", "closed"}:
            return SLAStatus(remaining_seconds=0, state="stopped", is_breached=False, should_escalate=False)

        remaining_seconds = int((deadline - now).total_seconds())
        if remaining_seconds <= 0:
            return SLAStatus(
                remaining_seconds=remaining_seconds,
                state="breached",
                is_breached=True,
                should_escalate=True,
            )

        if remaining_seconds <= WARNING_THRESHOLD_SECONDS:
            return SLAStatus(
                remaining_seconds=remaining_seconds,
                state="due_soon",
                is_breached=False,
                should_escalate=False,
            )

        return SLAStatus(
            remaining_seconds=remaining_seconds,
            state="on_track",
            is_breached=False,
            should_escalate=False,
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

