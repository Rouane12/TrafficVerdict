# Milestone 3 — Google Search Console setup

TrafficVerdict reuses the Google OAuth client created for Milestone 2. No new client secret is required.

## Google Cloud changes

In the existing `TrafficVerdict` Google Cloud project:

1. Enable **Google Search Console API**.
2. Open **Google Auth Platform → Data access** and add:

   `https://www.googleapis.com/auth/webmasters.readonly`

3. Open **Google Auth Platform → Clients → TrafficVerdict Local Development** and add this authorized redirect URI:

   `http://localhost:8000/api/integrations/search-console/callback`

4. Keep the app in Testing while developing. The same test user from Milestone 2 can be used.

## Local environment

The existing `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are reused.

The backend has local defaults for:

- `GOOGLE_SEARCH_CONSOLE_REDIRECT_URI=http://localhost:8000/api/integrations/search-console/callback`
- `GOOGLE_SEARCH_CONSOLE_SCOPE=https://www.googleapis.com/auth/webmasters.readonly`

They may be added explicitly to `backend/.env`, but are not required for local development.

## What the sync stores

TrafficVerdict selects a stable 28-day window ending on the newest finalized Search Console date and stores:

- clicks
- impressions
- CTR
- average position
- daily metrics
- top queries
- top pages

Search Console's API can return only top rows for dimensioned queries, so TrafficVerdict must not describe query/page breakdowns as a complete census of every row.

## Validation

1. Connect Search Console from the Neural Critic site card.
2. Choose the verified Neural Critic Search Console property.
3. Click **Sync now**.
4. Refresh the dashboard and confirm the selected property and metrics persist.
5. Confirm the GA4 integration still works independently.
