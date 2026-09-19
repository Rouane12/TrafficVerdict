# TrafficVerdict Public Beta Deployment

TrafficVerdict v1.0.0 is code-complete. The initial public launch strategy is free-first: get real users, repeat usage, and search traffic before adding billing.

This deployment path is intentionally low-cost and avoids requiring a payment method at the start:

- one Render free web service for the full TrafficVerdict app;
- one external PostgreSQL database such as Neon Free;
- GitHub Actions to wake the hosted app and trigger scheduled sync cycles.

Render's Free web service is suitable for a public beta but has limitations: it can spin down after inactivity and is not positioned by Render as production-grade infrastructure. Move to paid compute or another production host if usage becomes meaningful.

## 1. Database

Create a PostgreSQL database on a durable hosted provider. Neon Free works with TrafficVerdict's SQLAlchemy/PostgreSQL stack and can be used without changing the application schema.

Copy the database connection string and keep it private. TrafficVerdict accepts standard `postgresql://` or `postgres://` URLs and normalizes them to the psycopg SQLAlchemy driver automatically.

Do not commit the connection string.

## 2. Render service

TrafficVerdict deploys as one Docker web service.

The root `Dockerfile`:

1. builds the Next.js frontend as a static export;
2. installs the FastAPI backend;
3. copies the static frontend into the final image;
4. runs Alembic migrations on container startup;
5. launches FastAPI;
6. serves the frontend and `/api` from the same origin.

This avoids a second frontend server and keeps cookies/CORS simple.

Create a Render Blueprint from `render.yaml` after this deployment branch is merged to `main`.

The Blueprint creates a Free web service named `trafficverdict` in Frankfurt and generates:

- `AUTH_SECRET`;
- `CREDENTIAL_ENCRYPTION_SECRET`;
- `SYNC_TRIGGER_SECRET`.

It prompts for the database and Google OAuth values.

### Required Render variables

Set:

- `DATABASE_URL` — hosted PostgreSQL connection string;
- `GOOGLE_CLIENT_ID` — production Google OAuth client ID;
- `GOOGLE_CLIENT_SECRET` — production Google OAuth client secret;
- `GOOGLE_REDIRECT_URI`;
- `GOOGLE_SEARCH_CONSOLE_REDIRECT_URI`.

After Render assigns the final public URL, the redirect values are:

```text
https://YOUR-TRAFFICVERDICT-HOST/api/integrations/google/callback
https://YOUR-TRAFFICVERDICT-HOST/api/integrations/search-console/callback
```

Add those exact HTTPS callback URLs to the Google Cloud OAuth client as authorized redirect URIs.

The Blueprint sets `FRONTEND_ORIGIN` from Render's own public URL and enables Secure cookies automatically.

## 3. Scheduled sync

The deployment includes a protected endpoint:

```text
POST /api/internal/scheduled-sync
```

It accepts only:

```text
Authorization: Bearer <SYNC_TRIGGER_SECRET>
```

The endpoint runs one normal scheduler cycle. It does not enable the development-only force behavior.

The GitHub Actions workflow `.github/workflows/scheduled-sync.yml` calls this endpoint every six hours. TrafficVerdict's own 24-hour due logic still decides whether each provider actually needs a refresh.

Add these repository secrets in GitHub:

```text
TRAFFICVERDICT_URL=https://YOUR-TRAFFICVERDICT-HOST
TRAFFICVERDICT_SYNC_TRIGGER_SECRET=<same value as Render SYNC_TRIGGER_SECRET>
```

If those secrets are missing, the scheduled workflow exits successfully without doing anything.

## 4. First production smoke test

After the first deploy:

1. open `/api/health`;
2. confirm the public homepage loads;
3. register a new disposable test account;
4. create a site;
5. connect GA4;
6. connect Search Console;
7. connect Cloudflare;
8. run a manual sync;
9. verify Overview, Reconciliation, Tracking health, and Anomalies;
10. manually run the GitHub scheduled-sync workflow once and verify the provider sync timestamps update when due.

Do not migrate the existing local Neural Critic login/session cookie directly. Treat the hosted database as a fresh environment unless you intentionally migrate local data.

## 5. Free-tier limitations

Render Free web services can sleep after inactivity and wake on the next HTTP request. A sleeping service can therefore make the first request noticeably slower.

Render also states that Free web services are intended for testing, hobby projects, and previews rather than production-grade availability. For TrafficVerdict this is acceptable for the first public beta while we prove demand.

The database should not use Render's expiring Free Postgres tier. Use a durable external PostgreSQL free tier instead.

## 6. Upgrade trigger

Do not upgrade infrastructure just because it exists.

Upgrade once one of these becomes true:

- real users experience cold-start friction often;
- scheduled syncing becomes unreliable;
- database usage approaches free-tier limits;
- traffic or retention proves the product is worth keeping continuously available;
- the app begins producing meaningful ad or subscription revenue.

At that point, infrastructure cost is being justified by real usage rather than speculation.
