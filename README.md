# TrafficVerdict

Understand why your website analytics disagree — reconcile GA4, Search Console, and Cloudflare with evidence-backed explanations.

## Development status

Milestone 1 — Application Foundation: **complete and locally validated**.

Milestone 2 — Google Analytics Integration: **in progress**.

Current foundation:

- Next.js + TypeScript frontend
- FastAPI backend
- PostgreSQL for local development
- SQLAlchemy database layer
- Alembic migrations
- first-party authentication with protected workspace/site routes
- users, workspaces, workspace members, sites, and analytics connections
- Google OAuth connection flow
- GA4 account/property discovery
- encrypted provider credentials
- manual GA4 sync
- normalized GA4 metric snapshots
- `/api/health` smoke endpoint

See `docs/GA4_SETUP.md` for the local Google Cloud/OAuth setup required to test Milestone 2.

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
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── app/
│   └── lib/
├── docs/
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
