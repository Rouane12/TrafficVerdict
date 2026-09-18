# TrafficVerdict Security & Privacy Notes

This document describes the v1 implementation state. It is an engineering/security note, not a substitute for a published privacy policy or legal review.

## Data TrafficVerdict stores

TrafficVerdict stores only the data needed to provide analytics reconciliation:

- account email and optional display name;
- an Argon2 password hash (never the plaintext password);
- workspace and site metadata such as name, domain, and timezone;
- provider connection metadata;
- encrypted OAuth/API credentials required to refresh connected sources;
- aggregated GA4, Search Console, and Cloudflare metric snapshots;
- deterministic reconciliation/change-detection job metadata.

TrafficVerdict v1 does not intentionally ingest raw visitor-level event logs or advertising profiles.

## Provider permissions

The v1 integrations are read-oriented:

- Google Analytics: analytics read-only scope;
- Google Search Console: webmasters read-only scope;
- Cloudflare: a least-privilege API token with Zone Read and Analytics Read.

Cloudflare users create and control their own scoped token. Provider secrets must never be logged or returned by account-data exports.

## Credential protection

Provider credentials are encrypted before database storage. Production must use a strong credential-encryption secret that is different from the session-signing secret.

The API refuses to start with production settings that retain local-development secrets, insecure cookies, or non-HTTPS frontend/OAuth callback URLs.

Session cookies are HttpOnly. Production requires Secure cookies.

## Tenant isolation

Workspace membership is checked before workspace/site data is returned. Site-scoped analytics routes require membership in the site's workspace.

Automated regression tests cover cross-tenant access attempts for workspace listing, Cloudflare status, normalization, reconciliation, and change detection.

## OAuth state

Google OAuth state values are signed, short-lived tokens bound to both the signed-in user and the requested TrafficVerdict site. Callback routes verify that the state user matches the authenticated account before accepting the authorization result.

## Data export

An authenticated user can export the TrafficVerdict data available through their account. The export includes account/workspace/site metadata, connection metadata, aggregated metric snapshots, and sync-job history.

Exports intentionally exclude:

- password hashes;
- encrypted access tokens;
- encrypted refresh tokens;
- credential-encryption material;
- session tokens.

## Disconnect behavior

Disconnecting a provider clears its locally stored provider credentials and selected resource metadata.

Google Analytics revocation is attempted remotely on disconnect. Search Console currently clears the local grant without remote revocation because the v1 Google integrations can share the same Google OAuth client/grant; remotely revoking one can invalidate the other.

Existing historical metric snapshots are retained after a provider disconnect so TrafficVerdict can preserve past reconciliation context. A future retention control may allow users to remove a provider's historical snapshots separately.

## Account deletion

Account deletion requires:

1. the current password;
2. an explicit `DELETE` confirmation;
3. a final browser confirmation in the current UI.

For workspaces solely owned by the deleting user, deletion cascades through sites, connections, encrypted provider credentials, metric snapshots, and sync-job history.

If an owned workspace contains other members, deletion is blocked until ownership can be transferred, preventing accidental destruction of another user's workspace data.

Remote Google token revocation is best-effort during account deletion. Local credential deletion proceeds even if Google's revocation endpoint is temporarily unavailable.

## Retention

Current v1 retention behavior:

- account/profile data: retained until account deletion;
- provider credentials: retained until disconnect/account deletion or credential replacement;
- aggregated metric snapshots: retained while the owning workspace exists;
- sync-job history: retained while the owning site/workspace exists;
- disconnected-provider snapshots: retained for historical comparison;
- deleted solely owned workspaces/accounts: database rows are deleted through foreign-key cascades.

There is no automatic age-based snapshot pruning in v1. That policy should be revisited once real usage and storage costs are known.

## HTTP/browser protections

The API sends:

- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- `Referrer-Policy: same-origin`;
- a restrictive camera/microphone/geolocation Permissions Policy;
- `Cache-Control: no-store` for API responses.

The Next.js frontend sends the same baseline browser security headers.

For browser state-changing requests, the API rejects an explicitly supplied `Origin` header when it does not match the configured frontend origin. This supplements SameSite cookies and the single-origin CORS policy.

## Logging

Application code must not print or log OAuth tokens, Cloudflare API tokens, session cookies, passwords, authorization headers, or encryption secrets.

Provider errors shown to users should contain provider-safe error messages/status information rather than full request headers or secret-bearing payloads.

## Before a public production launch

The following remain deployment/review tasks rather than local-v1 features:

- deploy behind HTTPS;
- use production-only high-entropy secrets;
- configure production Google OAuth callback URLs;
- configure production database backups and access controls;
- review dependency/security alerts;
- verify cookies and CORS against the final domains;
- publish a user-facing privacy policy and terms as appropriate;
- perform a final security review against the deployed environment.

Do not treat passing local tests as a substitute for that deployment review.
