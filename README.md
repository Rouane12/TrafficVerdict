# TrafficVerdict

Understand why your website analytics disagree — reconcile GA4, Search Console, and Cloudflare with evidence-backed explanations.

## Development status

Milestone 1: Application Foundation.

Current foundation:

- Next.js + TypeScript frontend shell
- FastAPI backend
- PostgreSQL for local development
- SQLAlchemy database layer
- Alembic migrations
- core models for users, workspaces, workspace members, sites, and analytics connections
- environment configuration
- `/api/health` smoke endpoint
- backend smoke test

Authentication and protected workspace/site routes are the next Milestone 1 step.

## Repository structure

```text
TrafficVerdict/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   └── main.py
│   └── tests/
├── frontend/
│   └── app/
├── docker-compose.yml
└── README.md
```

## Run the local database

```bash
docker compose up -d postgres
```

## Run database migrations

From `backend/` after installing the Python dependencies:

```bash
alembic upgrade head
```

## Run the backend

From `backend/`:

```bash
python -m venv .venv
```

Activate the virtual environment, then:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` and the health check at `http://localhost:8000/api/health`.

## Run the frontend

From `frontend/`:

```bash
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Product rule

TrafficVerdict is not another generic analytics dashboard. Its purpose is to explain meaningful disagreement between analytics sources, surface tracking-health problems, and show the evidence behind every diagnosis.
