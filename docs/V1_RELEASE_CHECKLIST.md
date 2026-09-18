# TrafficVerdict v1 Release Checklist

TrafficVerdict v1 is intentionally launching as a free product first. Billing is not a v1 launch blocker. The initial goal is to prove usage, repeat visits, and trusted reconciliation before deciding what should become paid.

## Core product

- [x] First-party account registration/login/logout
- [x] Workspaces and sites
- [x] GA4 connection, property discovery, sync, disconnect
- [x] Search Console connection, property discovery, sync, disconnect
- [x] Cloudflare token flow, zone discovery, sync, disconnect
- [x] Normalized overlapping evidence window
- [x] Deterministic reconciliation findings
- [x] Evidence drawer
- [x] Tracking-health summary
- [x] Date-window controls
- [x] Mobile dashboard behavior
- [x] Durable scheduled-sync jobs
- [x] Retry/deduplication
- [x] Daily and week-over-week change detection
- [x] Real anomaly view
- [x] Account data export
- [x] Account deletion

## Automated validation

- [x] Backend pytest suite
- [x] Tenant-isolation regression coverage
- [x] Production-config guardrail tests
- [x] Account export/deletion tests
- [x] Frontend TypeScript check
- [x] Frontend production build in CI
- [x] GitHub Actions validation on milestone/v1 branches and pull requests

## Security/privacy implementation

- [x] Provider credentials encrypted at rest
- [x] Read-only/minimum provider permissions
- [x] HttpOnly session cookie
- [x] Secure-cookie requirement in production
- [x] HTTPS requirement in production config
- [x] Distinct strong auth/encryption secrets required in production
- [x] OAuth state signed, short-lived, and account/site bound
- [x] Cross-tenant authorization tests
- [x] Baseline browser/API security headers
- [x] API responses marked no-store
- [x] Export excludes passwords and provider credentials
- [x] Retention behavior documented

See `docs/SECURITY_PRIVACY.md`.

## Local proof already completed

- [x] Real Neural Critic GA4 data synced
- [x] Real Neural Critic Search Console data synced
- [x] Real Neural Critic Cloudflare data synced
- [x] Reconciliation findings verified against real data
- [x] Tracking health verified
- [x] Anomaly comparison verified
- [x] Forced scheduled-sync probe queued all three providers and completed successfully

## Still required before public deployment

- [ ] Choose production hosting for frontend, API/worker, and PostgreSQL
- [ ] Configure production HTTPS domains
- [ ] Generate production-only high-entropy secrets
- [ ] Configure production Google OAuth redirect URLs
- [ ] Run Alembic migrations against production DB
- [ ] Run worker as a continuously supervised process/service
- [ ] Configure backups and recovery for PostgreSQL
- [ ] Verify final CORS/cookie behavior on real domains
- [ ] Smoke-test registration and all three provider onboarding flows in production
- [ ] Publish user-facing Privacy and Terms pages appropriate to the launch
- [ ] Perform final deployed security review

## Initial growth strategy

TrafficVerdict launches free. The first business objective is not paid conversion; it is trusted usage.

Measure:

- visitors;
- account registrations;
- first source connected;
- all three sources connected;
- first verdict reached;
- evidence views;
- repeat weekly users.

Build public, genuinely useful search pages around problems such as:

- Cloudflare vs GA4;
- GA4 vs Search Console;
- why analytics numbers do not match;
- Cloudflare traffic vs visitors;
- Search Console clicks vs GA4 sessions;
- how to know if GA4 tracking is broken;
- bot/network traffic vs real traffic;
- why GA4 suddenly dropped.

Advertising can be considered on suitable public editorial/help pages after meaningful traffic exists. The logged-in analytics product should remain clarity-first rather than ad-heavy.

Subscriptions/payment infrastructure can be revisited only after usage data shows what users value enough to pay for.
