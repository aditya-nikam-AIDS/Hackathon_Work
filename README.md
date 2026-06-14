# Customer Complaint Classification & Routing Engine

End-to-end hackathon system for classifying incoming customer complaints, assigning priority, routing to the right support team, and tracking SLA countdowns in real time.

The implementation is intentionally modular:

- FastAPI backend for ingestion, classification, routing, SLA, and dashboard APIs.
- Local LLM integration through Ollama, defaulting to `llama3.2`.
- Local TF-IDF classifier training path with scikit-learn.
- Deterministic keyword fallback so the demo works even without an LLM.
- SQLite by default for local use; PostgreSQL via Docker Compose for a production-like run.
- Streamlit dashboard for live ticket queue, SLA countdown, filters, and escalation alerts.

## Architecture

```text
                           +--------------------------+
                           |   Streamlit Dashboard    |
                           | filters, SLA countdowns  |
                           +------------+-------------+
                                        |
                                        | GET /dashboard, GET /tickets
                                        v
+-------------+   POST /create-ticket   +-------------+      +------------------+
| Channels    +------------------------->+ FastAPI API +----->+ Ticket Service   |
| web, email, |                          +------+------+      +---------+--------+
| chat, CRM   |                                 |                       |
+-------------+                                 |                       v
                                                |              +--------+---------+
                                                |              | Processing Layer |
                                                |              +--------+---------+
                                                |                       |
                                                v                       v
                                      +---------+--------+   +----------+----------+
                                      | Database         |   | LLM / TF-IDF /      |
                                      | SQLite/Postgres  |   | Keyword Classifier  |
                                      +---------+--------+   +----------+----------+
                                                ^                       |
                                                |                       v
                                      +---------+--------+   +----------+----------+
                                      | SLA Worker       |   | Rule + Routing     |
                                      | escalations      |   | Engines            |
                                      +------------------+   +---------------------+
```

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| Ingestion API | Accepts complaint text and customer metadata through `POST /create-ticket`. |
| Processing Engine | Orchestrates classification, sentiment, priority, routing, SLA, and persistence. |
| ML Model | Uses local LLM when configured, local TF-IDF model when trained, and keyword fallback otherwise. |
| Rule Engine | Converts sentiment, keywords, category, and customer tier into priority. |
| Routing Engine | Maps category and overrides to operational teams. |
| SLA Engine | Assigns deadlines by priority and computes countdown, due-soon, breached states. |
| Database | Stores every ticket, decision, SLA deadline, status, and escalation timestamp. |
| Dashboard | Shows ticket queue, filters, charts, SLA countdowns, and escalation alerts. |

## Data Flow

1. A channel sends complaint text to `POST /create-ticket`.
2. Backend cleans text and classifies category using `llama3.2`, trained TF-IDF, or keyword fallback.
3. Sentiment is scored by the LLM or the local lexicon scorer.
4. Priority engine evaluates sentiment, critical keywords, category risk, and customer tier.
5. Routing engine maps the category to a team and applies VIP/security overrides.
6. SLA engine assigns a deadline based on priority.
7. Ticket is stored in the database with the full decision trail.
8. Dashboard polls `GET /dashboard` and shows countdowns and escalation alerts.
9. Worker or dashboard request marks breached tickets as escalated.

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
|   |   |-- workers/             # background escalation worker
|   |   `-- main.py              # FastAPI application
|   `-- tests/                   # focused engine tests
|-- data/                        # sample labeled complaints
|-- docs/                        # architecture, API, production notes
|-- frontend/                    # Streamlit dashboard
|-- models/                      # trained classifier artifacts
|-- scripts/                     # training and seeding utilities
|-- docker-compose.yml
|-- Dockerfile.backend
|-- Dockerfile.dashboard
|-- requirements.txt
`-- .env.example
```

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Train the optional local classifier:

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

Seed demo tickets:

```bash
python scripts/seed_demo_data.py --api-url http://localhost:8000
```

## Local LLM Configuration

Local Ollama example:

```bash
ollama pull llama3.2
```

Set `.env`:

```env
LLM_PROVIDER=ollama
LLM_API_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
USE_LLM_CLASSIFIER=true
```

OpenAI-compatible endpoint example:

```env
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=https://your-provider.example.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=your-model-name
```

If the LLM is unavailable or returns low confidence, the backend automatically falls back to the trained TF-IDF model, then keyword rules.

## API Examples

Create a ticket:

```bash
curl -X POST http://localhost:8000/create-ticket ^
  -H "Content-Type: application/json" ^
  -d "{\"complaint_text\":\"My account was hacked and there is an unauthorized transaction.\",\"customer_id\":\"CUST-42\",\"customer_tier\":\"vip\",\"metadata\":{\"source\":\"chat\"}}"
```

Response:

```json
{
  "id": "uuid",
  "category": "fraud_security",
  "priority": "critical",
  "team": "Security Incident Desk",
  "sla_deadline": "2026-06-13T12:00:00Z",
  "sla_remaining_seconds": 7199,
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

## SLA Rules

| Priority | SLA |
| --- | --- |
| Critical | 2 hours |
| High | 8 hours |
| Medium | 24 hours |
| Low | 72 hours |

SLA states:

- `on_track`: deadline is more than 30 minutes away.
- `due_soon`: deadline is within 30 minutes.
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
