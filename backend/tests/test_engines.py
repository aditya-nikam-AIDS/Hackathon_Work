from datetime import datetime, timedelta, timezone

from backend.app.services.priority_engine import PriorityEngine
from backend.app.services.routing_engine import RoutingEngine
from backend.app.services.sla_engine import SLAEngine


def test_priority_engine_promotes_fraud_vip_complaint_to_critical():
    decision = PriorityEngine().decide(
        text="My account was hacked and this unauthorized charge is fraud.",
        category="fraud_security",
        sentiment_score=-0.8,
        customer_tier="vip",
    )

    assert decision.priority == "critical"
    assert decision.score >= 4.5


def test_routing_engine_sends_high_fraud_to_security_incident_desk():
    decision = RoutingEngine().route(category="fraud_security", priority="high", customer_tier="standard")

    assert decision.team == "Security Incident Desk"


def test_sla_engine_detects_breach():
    now = datetime.now(timezone.utc)
    status = SLAEngine().status_for(
        deadline=now - timedelta(minutes=1),
        ticket_status="open",
        now=now,
    )

    assert status.state == "breached"
    assert status.should_escalate is True


def test_sla_engine_stops_countdown_for_resolved_ticket():
    now = datetime.now(timezone.utc)
    status = SLAEngine().status_for(
        deadline=now - timedelta(hours=1),
        ticket_status="resolved",
        now=now,
    )

    assert status.state == "stopped"
    assert status.should_escalate is False

