# API Contract

## POST /create-ticket

Request:

```json
{
  "complaint_text": "I was charged twice and need a refund now.",
  "customer_id": "CUST-1001",
  "customer_tier": "premium",
  "metadata": {
    "source": "chat",
    "order_id": "ORD-9001"
  }
}
```

Response:

```json
{
  "id": "generated-uuid",
  "complaint_text": "I was charged twice and need a refund now.",
  "customer_id": "CUST-1001",
  "customer_tier": "premium",
  "metadata": {
    "source": "chat",
    "order_id": "ORD-9001"
  },
  "category": "billing",
  "classification_confidence": 0.8,
  "classification_source": "keyword_fallback",
  "sentiment_score": -0.5,
  "priority": "high",
  "priority_reason": "high_keywords=refund now; negative_sentiment; customer_tier=premium; category=billing",
  "team": "Billing Operations",
  "status": "open",
  "sla_deadline": "2026-06-13T10:00:00Z",
  "sla_remaining_seconds": 28799,
  "sla_state": "on_track",
  "escalated_at": null,
  "created_at": "2026-06-13T02:00:00Z",
  "updated_at": "2026-06-13T02:00:00Z"
}
```

## GET /tickets

Query parameters:

- `priority`: `critical`, `high`, `medium`, `low`
- `team`: assigned team name
- `status`: `open`, `in_progress`, `resolved`, `closed`
- `category`: complaint category
- `limit`: 1 to 500

Example:

```bash
curl "http://localhost:8000/tickets?priority=high&status=open&limit=50"
```

## GET /dashboard

Returns:

- total/open/escalated counts
- breached and due-soon counts
- aggregation by priority/team/category
- top alert tickets
- recent tickets with SLA countdown

## POST /run-escalations

Manually marks breached open tickets as escalated. The dashboard and ticket list also call this logic before returning data.

