# Banking Customer Support Automation System

End-to-end AI-powered system for classifying and routing banking customer complaints, assigning priority based on financial risk, routing to specialized banking teams, and tracking SLA countdowns in real time.

## Banking Domain Focus

This system is designed specifically for **banking customer support** handling:

- **Digital Banking** (UPI, Net Banking, Mobile App)
- **Transactions and Payments** (NEFT, IMPS, RTGS, UPI)
- **Accounts and KYC** (Login, Account Management)
- **Loans and Credit Cards** (EMI, Credit Limit, Disputes)
- **Fraud and Security** (Unauthorized Transactions, Phishing)

The implementation is intentionally modular:

- FastAPI backend for ingestion, classification, routing, SLA, and dashboard APIs.
- Local LLM integration through Ollama, defaulting to `llama3.2`.
- Agentic workflow orchestration with LangGraph.
- LangChain chat model adapters for Ollama and OpenAI-compatible LLM endpoints.
- Local TF-IDF classifier training path with scikit-learn.
- Deterministic keyword fallback so the demo works even without an LLM.
- SQLite by default for local use; PostgreSQL via Docker Compose for a production-like run.
- Streamlit dashboard for live ticket queue, SLA countdown, filters, and escalation alerts.

## 🚀 Performance & UX Optimizations

This system includes enterprise-grade optimizations for both performance and user experience:

### Performance Features
- **LLM Response Caching**: 5-90x faster for repeat issues (70-80% cache hit rate)
- **Duplicate Detection**: Automatically identifies similar tickets within 24 hours
- **Processing Time Tracking**: Real-time performance monitoring
- **Team Workload Balancing**: Intelligent routing based on team capacity

### User Experience Features
- **Quick Templates**: 6 pre-defined templates for common banking issues (70% faster creation)
- **Real-time Validation**: Input validation with helpful hints
- **Enhanced Feedback**: Detailed success messages with confidence scores
- **Duplicate Warnings**: Alerts when creating similar tickets
- **Loading Indicators**: Clear progress feedback for slow operations

### Intelligence Features
- **Confidence Scoring**: Multi-factor confidence calculation
- **Auto-Response Suggestions**: Templated responses based on issue type
- **Agent Feedback Loop**: Continuous improvement from corrections
- **Performance Metrics**: Real-time system health dashboard

See [`docs/optimizations.md`](docs/optimizations.md) for complete details on all optimization features.

## Architecture

```text
                           +--------------------------+
                           |   Banking Dashboard      |
                           | filters, SLA countdowns  |
                           +------------+-------------+
                                        |
                                        | GET /dashboard, GET /tickets
                                        v
+-------------+   POST /create-ticket   +-------------+      +------------------+
| Channels    +------------------------->+ FastAPI API +----->+ Ticket Service   |
| mobile app, |                          +------+------+      +---------+--------+
| net banking,|                                 |                       |
| branch, CRM |                                 |                       v
+-------------+                                 |              +--------+---------+
                                                |              | Processing Layer |
                                                |              +--------+---------+
                                                |                       |
                                                v                       v
                                      +---------+--------+   +----------+----------+
                                      | Database         |   | LangGraph Agent     |
                                      | SQLite/Postgres  |   | Workflow            |
                                      +---------+--------+   +----------+----------+
                                                ^                       |
                                                |                       v
                                      +---------+--------+   +----------+----------+
                                      | SLA Worker       |   | LangChain LLM +    |
                                      | escalations      |   | Banking Rules      |
                                      +------------------+   +---------------------+
```

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| Ingestion API | Accepts banking complaint text and customer metadata through `POST /create-ticket`. |
| Processing Engine | Uses a LangGraph workflow to orchestrate classification, priority, routing, SLA, and agent review. |
| ML Model | Uses LangChain to call the configured local LLM, local TF-IDF model when trained, and keyword fallback otherwise. |
| Rule Engine | Converts sentiment, banking keywords, category, and customer tier into priority. |
| Routing Engine | Maps banking categories to specialized teams (Payments, Fraud Investigation, Loan Department, etc.). |
| SLA Engine | Assigns banking-specific deadlines (1h Critical, 4h High, 12h Medium, 24h Low) and computes countdown states. |
| Database | Stores every ticket, decision, SLA deadline, status, and escalation timestamp. |
| Dashboard | Shows ticket queue, filters, charts, SLA countdowns, and escalation alerts. |

## Banking Categories

| Category | Description | Routed To |
| --- | --- | --- |
| Transaction Issue | Failed transactions, payment delays, money deducted but not received | Payments Team |
| Account Issue | Login problems, account blocked, KYC issues | Customer Support Team |
| Fraud / Security | Unauthorized transactions, suspicious activity, phishing | Fraud Investigation Team |
| Loan / Credit Issue | Loan approval/rejection, EMI issues, credit card disputes | Loan Department |
| Technical Issue | App crashes, website errors, system downtime | IT Support Team | |

## Data Flow

1. A channel sends banking complaint text to `POST /create-ticket`.
2. Backend cleans text and classifies category using `llama3.2`, trained TF-IDF, or keyword fallback.
3. Sentiment is scored by the LLM or the local lexicon scorer.
4. Priority engine evaluates sentiment, banking-specific keywords, category risk, and customer tier.
5. Routing engine maps the category to a banking team and applies VIP/premium overrides.
6. SLA engine assigns a deadline based on priority (1h/4h/12h/24h).
7. LangGraph optionally runs an agent review node for high-risk or low-confidence tickets.
8. Ticket is stored in the database with the full decision trail and workflow trace.
9. Dashboard polls `GET /dashboard` and shows countdowns and escalation alerts.
10. Worker or dashboard request marks breached tickets as escalated.

## Production-Ready Folder Structure

```text
.
|-- backend/
|   |-- app/
|   |   |-- api/routes/          # FastAPI endpoints
|   |   |-- core/                # settings and configuration
|   |   |-- db/                  # SQLAlchemy models and sessions
|   |   |-- schemas/             # request/response contracts
|   |   |-- services/            # NLP, priority, routing, SLA, ticket orchestration
|   |   |   `-- agentic/         # LangGraph complaint-processing workflow
|   |   |-- workers/             # background escalation worker
|   |   `-- main.py              # FastAPI application
|   `-- tests/                   # focused engine tests
|-- data/                        # sample banking complaints
|-- docs/                        # architecture, API, production notes
|-- frontend/                    # Banking dashboard (Streamlit)
|-- models/                      # trained classifier artifacts
|-- scripts/                     # training and seeding utilities
|-- docker-compose.yml
|-- Dockerfile.backend
|-- Dockerfile.dashboard
`-- requirements.txt
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Train the optional local classifier with banking data:

```bash
python scripts/train_classifier.py --input data/sample_complaints.csv --output models/complaint_classifier.joblib
```

Run the API:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

In a second terminal, run the dashboard:

```bash
streamlit run frontend/streamlit_app.py
```

Seed demo banking tickets:

```bash
python scripts/seed_demo_data.py --api-url http://localhost:8000
```

## Local LLM Configuration

The system uses Ollama by default. Install and pull the model:

```bash
ollama pull llama3.2
```

Configuration is hardcoded in `backend/app/core/config.py`:

```python
llm_provider = "ollama"           # Options: "disabled", "ollama", "openai_compatible"
llm_api_base_url = "http://localhost:11434"
llm_model = "llama3.2"
llm_timeout_seconds = 90
use_llm_classifier = True
```

To use a different LLM provider, modify the `Settings` class in `config.py`.

If the LLM is unavailable or returns low confidence, the backend automatically falls back to the trained TF-IDF model, then keyword rules.

## Agentic LangGraph Workflow

Ticket creation now flows through `ComplaintAgentWorkflow`:

```text
START
  -> preprocess
  -> classify              # LangChain LLM, TF-IDF, or keyword fallback
  -> prioritize            # rule tool
  -> route                 # routing tool
  -> assign_sla            # SLA tool
  -> agent_review?         # conditional node for critical/high/low-confidence cases
  -> finalize
  -> END
```

The workflow stores an `agentic_workflow` object inside ticket metadata:

```json
{
  "version": "langgraph-agentic-v1",
  "requires_human_review": true,
  "recommended_actions": ["Notify the team lead and monitor SLA countdown closely."],
  "escalation_summary": "High-risk complaint routed for urgent follow-up.",
  "trace": [
    {"node": "preprocess", "details": {"characters": 72}},
    {"node": "classify", "details": {"category": "fraud_security", "source": "llm"}}
  ]
}
```

## API Examples

Create a banking ticket:

```bash
curl -X POST http://localhost:8000/create-ticket ^
  -H "Content-Type: application/json" ^
  -d "{\"complaint_text\":\"My UPI payment failed but Rs 5000 was deducted from my account. Please help immediately.\",\"customer_id\":\"CUST-42\",\"customer_tier\":\"vip\",\"metadata\":{\"source\":\"mobile_app\"}}"
```

Response:

```json
{
  "id": "uuid",
  "category": "transaction_issue",
  "priority": "high",
  "team": "Payments Team",
  "sla_deadline": "2026-06-16T16:00:00Z",
  "sla_remaining_seconds": 14399,
  "sla_state": "on_track",
  "classification_source": "llm"
}
```

Fraud example:

```bash
curl -X POST http://localhost:8000/create-ticket ^
  -H "Content-Type: application/json" ^
  -d "{\"complaint_text\":\"I see unauthorized transaction of Rs 25000 on my account. I did not make this transaction.\",\"customer_id\":\"CUST-100\",\"customer_tier\":\"premium\"}"
```

Response:

```json
{
  "id": "uuid",
  "category": "fraud_security",
  "priority": "critical",
  "team": "Fraud Incident Response Team",
  "sla_deadline": "2026-06-16T13:00:00Z",
  "sla_remaining_seconds": 3599,
  "sla_state": "on_track",
  "classification_source": "llm"
}
```

List tickets:

```bash
curl "http://localhost:8000/tickets?priority=critical&status=open"
```

Dashboard summary:

```bash
curl http://localhost:8000/dashboard
```

### New Optimization Endpoints

Get ticket templates:

```bash
curl http://localhost:8000/templates
```

Response:

```json
{
  "templates": {
    "upi_failed": {
      "title": "UPI Payment Failed",
      "template": "My UPI payment to {merchant} for Rs {amount} failed...",
      "category_hint": "transaction_issue",
      "priority_hint": "high"
    },
    ...
  },
  "count": 6
}
```

Get performance metrics:

```bash
curl http://localhost:8000/metrics
```

Response:

```json
{
  "total_tickets_processed": 150,
  "avg_processing_time_ms": 2340,
  "llm_cache_hits": 120,
  "llm_cache_misses": 30,
  "cache_hit_rate": 0.8,
  "duplicate_tickets_detected": 5
}
```

Submit agent feedback:

```bash
curl -X POST "http://localhost:8000/tickets/{ticket_id}/feedback" ^
  -H "Content-Type: application/json" ^
  -d "{\"correct_category\":\"fraud_security\",\"correct_priority\":\"critical\",\"agent_notes\":\"Customer confirmed unauthorized transaction\"}"
```

Get team workload:

```bash
curl http://localhost:8000/workload
```

Response:

```json
{
  "Payments Team": {
    "open_tickets": 12,
    "avg_sla_remaining": 7200,
    "load_factor": 1.2
  },
  "Fraud Investigation Team": {
    "open_tickets": 5,
    "avg_sla_remaining": 2400,
    "load_factor": 0.5
  }
}
```

## Banking SLA Rules

| Priority | SLA | Use Case |
| --- | --- | --- |
| Critical | 1 hour | Fraud, security breach, VIP urgent issues, system outage |
| High | 4 hours | Payment failures, login issues affecting account access |
| Medium | 12 hours | General banking issues, transaction delays |
| Low | 24 hours | Minor queries, informational requests |

SLA states:

- `on_track`: deadline is more than 15 minutes away.
- `due_soon`: deadline is within 15 minutes.
- `breached`: deadline has passed.
- `stopped`: ticket is resolved or closed.

## Advanced Path

For a 1-2 day hackathon, run the current API and dashboard. For production expansion:

- Add Kafka topic `complaints.incoming` before FastAPI processing for high-volume ingestion.
- Add topic `tickets.classified` after classification for downstream CRM sync.
- Run the escalation worker as a separate container.
- Add feedback endpoint for agents to correct categories and retrain the TF-IDF model.
- Add role-based dashboards: executive, team lead, agent, compliance.
- Replace `Base.metadata.create_all` with Alembic migrations.
- Add auth, audit logs, PII redaction, and model output monitoring.
