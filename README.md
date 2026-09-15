# TrafficVerdict

Understand why your website analytics disagree — reconcile GA4, Search Console, and Cloudflare with evidence-backed explanations.

## Development status

Milestone 1: Application Foundation.

Current foundation:

- FastAPI backend
- PostgreSQL for local development
- SQLAlchemy database layer
- environment configuration
- `/api/health` smoke endpoint
- backend smoke test
- monorepo-ready structure for the upcoming Next.js frontend

## Repository structure

```text
TrafficVerdict/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   └── main.py
│   └── tests/
├── frontend/              # added next
├── docker-compose.yml
└── README.md
```

## Run the local database

```bash
docker compose up -d postgres
```

## Run the backend

From `backend/`:

```bash
python -m venv .venv
```

Activate the virtual environment, then:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` and the health check at `http://localhost:8000/api/health`.

## Product rule

TrafficVerdict is not another generic analytics dashboard. Its purpose is to explain meaningful disagreement between analytics sources, surface tracking-health problems, and show the evidence behind every diagnosis.
