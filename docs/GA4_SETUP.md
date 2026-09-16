# TrafficVerdict — Google Analytics setup

Milestone 2 uses a server-side OAuth 2.0 flow. TrafficVerdict requests only the read-only Google Analytics scope and keeps provider tokens on the FastAPI backend.

## 1. Create or select a Google Cloud project

Use a dedicated project for TrafficVerdict development.

## 2. Enable both Analytics APIs

Enable:

- Google Analytics Data API
- Google Analytics Admin API

The Admin API is used to discover the GA4 accounts/properties the user can access. The Data API is used to fetch report metrics for the selected property.

## 3. Configure Google OAuth

Create an OAuth 2.0 client with application type **Web application**.

For local development add this exact authorized redirect URI:

```text
http://localhost:8000/api/integrations/google/callback
```

If the OAuth app is in testing mode, add the Google account you will use for Neural Critic as a test user.

TrafficVerdict requests this scope only:

```text
https://www.googleapis.com/auth/analytics.readonly
```

## 4. Create `backend/.env`

Copy `backend/.env.example` to `backend/.env` and fill in the Google values:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/integrations/google/callback
```

Do not commit the `.env` file.

Also replace the development secrets with random values. From PowerShell you can generate each secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Use separate generated values for:

```env
AUTH_SECRET=...
CREDENTIAL_ENCRYPTION_SECRET=...
```

## 5. Make sure the Google account has GA4 access

The Google account used during OAuth must already have access to the GA4 property you want TrafficVerdict to read.

## 6. Apply the Milestone 2 migration

From `backend/`:

```powershell
pip install -r requirements.txt
alembic upgrade head
```

## Milestone 2 flow

```text
TrafficVerdict site
    ↓
Connect Google Analytics
    ↓
Google OAuth consent
    ↓
TrafficVerdict discovers accessible GA4 properties
    ↓
User selects the correct property
    ↓
Manual sync fetches the latest 28 complete days
    ↓
Normalized GA4 snapshot is stored in PostgreSQL
```

The initial normalized snapshot stores:

- active users
- sessions
- views
- engaged sessions
- daily values for the same metrics

OAuth access and refresh tokens are encrypted before being persisted.
