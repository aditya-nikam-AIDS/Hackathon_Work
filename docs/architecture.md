# Architecture and Data Flow

## Suggested Tech Stack

| Layer | Hackathon Choice | Production Upgrade |
| --- | --- | --- |
| API | FastAPI | FastAPI behind API gateway |
| NLP | Local LLM + TF-IDF fallback | Model service, model registry, batch evaluation |
| Rules | Python services | Versioned rules in database or policy engine |
| Database | SQLite local, PostgreSQL in Docker | Managed PostgreSQL with replicas |
| Dashboard | Streamlit | React, WebSocket, RBAC |
| Queue | Optional worker loop | Kafka or RabbitMQ |
| Observability | Logs | OpenTelemetry, metrics, traces |

## End-to-End Workflow

```text
Incoming complaint
  -> validate request
  -> classify complaint category
  -> score sentiment
  -> apply priority rules
  -> route to team
  -> assign SLA deadline
  -> persist ticket
  -> expose dashboard metrics
  -> escalate if breached
```

## NLP Strategy

The classifier uses layered reliability:

1. Local LLM, for example `llama3.2`: best semantic understanding when an LLM endpoint is configured.
2. TF-IDF classifier: fast local model trained with `scripts/train_classifier.py`.
3. Keyword fallback: deterministic category mapping for demos and outages.

The LLM prompt forces strict JSON:

```json
{
  "category": "billing",
  "sentiment_score": -0.7,
  "urgency_signals": ["charged twice", "refund now"],
  "confidence": 0.91,
  "reason": "Billing complaint with refund urgency."
}
```

## Priority Engine

Priority is a hybrid decision:

```text
priority_score =
  keyword risk
  + negative sentiment risk
  + customer tier weight
  + category risk
```

Thresholds:

- `critical`: score >= 4.5
- `high`: score >= 2.75
- `medium`: score >= 1.0
- `low`: otherwise

## Routing Engine

Default mapping:

| Category | Team |
| --- | --- |
| billing | Billing Operations |
| technical | Technical Support |
| delivery | Logistics Support |
| product_quality | Quality Assurance |
| account | Account Operations |
| fraud_security | Security Response |
| refund | Refunds Desk |
| general | Customer Care |

Overrides:

- High or critical fraud/security issues go to `Security Incident Desk`.
- VIP critical issues go to `Executive Support` unless the security override applies first.

## Database Design

Table: `tickets`

| Column | Purpose |
| --- | --- |
| id | Ticket UUID |
| complaint_text | Original customer complaint |
| customer_id | CRM/customer reference |
| customer_tier | `vip`, `premium`, `standard`, `trial` |
| metadata_json | Source and extra payload |
| category | ML/LLM category |
| classification_confidence | Classifier confidence |
| classification_source | `llm`, `tfidf_model`, or `keyword_fallback` |
| sentiment_score | -1 to 1 |
| priority | `critical`, `high`, `medium`, `low` |
| priority_reason | Explainable signals |
| team | Assigned team |
| status | Ticket lifecycle state |
| sla_deadline | Deadline timestamp |
| escalated_at | Timestamp when SLA breach was escalated |
| created_at, updated_at | Audit timestamps |

Indexes:

- `(priority, status)` for critical queues.
- `(team, status)` for team dashboards.
- `sla_deadline` for escalation scans.
- `created_at` for recent-ticket views.
