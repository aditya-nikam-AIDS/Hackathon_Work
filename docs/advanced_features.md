# Advanced Features

## Kafka Design

Topics:

- `complaints.incoming`: raw requests from web, email, chat, CRM.
- `complaints.classified`: category and sentiment decisions.
- `tickets.routed`: priority, team, and SLA deadline assigned.
- `tickets.escalated`: SLA breaches and escalation events.
- `labels.corrected`: human feedback for retraining.

Flow:

```text
Channel adapters -> complaints.incoming
Classifier worker -> complaints.classified
Routing worker -> tickets.routed
Ticket writer -> PostgreSQL
SLA worker -> tickets.escalated
Feedback UI -> labels.corrected -> retraining pipeline
```

## Real-Time Updates

The Streamlit dashboard polls for hackathon simplicity. Production options:

- FastAPI WebSocket endpoint for ticket updates.
- Server-sent events for SLA countdown and alerts.
- Kafka consumer that pushes updates into Redis pub/sub.

## LangGraph Production Path

- Add a checkpointer to persist graph state between nodes.
- Stream graph events to the dashboard for live workflow visibility.
- Add a human-in-the-loop interrupt before finalizing critical security tickets.
- Send traces to LangSmith for debugging, prompt evaluation, and regression checks.

## Feedback Loop

Agents should be able to correct:

- category
- priority
- assigned team
- false escalation

Store corrections in a `ticket_feedback` table and export to a labeled dataset. Retrain the TF-IDF model nightly and evaluate LLM prompt quality against human labels.

## Role-Based Dashboards

Roles:

- Agent: assigned team queue.
- Team lead: SLA risk, backlog, escalations.
- Executive: priority mix, breach trend, top complaint categories.
- Compliance: fraud/security and audit trail.

## Production Hardening

- Add authentication and authorization.
- Redact PII before sending text to external LLM providers.
- Add Alembic migrations.
- Add structured JSON logging and OpenTelemetry.
- Add model/version fields to tickets.
- Add retry and circuit breaker around LLM calls.
- Add dead-letter queue for failed processing.
