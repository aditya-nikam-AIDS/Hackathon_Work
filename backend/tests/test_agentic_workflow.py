import asyncio
from datetime import datetime, timezone

from backend.app.core.config import Settings
from backend.app.services.agentic.workflow import ComplaintAgentWorkflow


def test_agentic_workflow_processes_critical_security_ticket_without_llm():
    settings = Settings(LLM_PROVIDER="disabled")
    workflow = ComplaintAgentWorkflow(settings)

    decision = asyncio.run(
        workflow.process(
            complaint_text="My account was hacked and there is an unauthorized transaction.",
            customer_id="CUST-TEST",
            customer_tier="vip",
            metadata={"source": "test"},
            created_at=datetime.now(timezone.utc),
        )
    )

    assert decision.classification.category == "fraud_security"
    assert decision.priority_decision.priority == "critical"
    assert decision.routing_decision.team == "Security Incident Desk"
    assert decision.requires_human_review is True
    assert decision.recommended_actions
    assert decision.agent_trace[-1]["node"] == "finalize"
