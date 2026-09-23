#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://trafficverdict.app"

REQUIRED_ARTIFACTS = (
    "Dockerfile",
    "render.yaml",
    ".github/workflows/ci.yml",
    ".github/workflows/scheduled-sync.yml",
    "frontend/app/privacy/page.tsx",
    "frontend/app/terms/page.tsx",
    "frontend/app/robots.ts",
    "frontend/app/sitemap.ts",
)

EXPECTED_GOOGLE_REDIRECTS = (
    "/api/integrations/google/callback",
    "/api/integrations/search-console/callback",
)


@dataclass
class Check:
    key: str
    label: str
    status: str
    detail: str
    blocking: bool = True


def _request(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 25.0,
) -> tuple[int, dict[str, str], str]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    payload = None
    request_headers = {
        "User-Agent": "TrafficVerdict-LaunchDoctor/1.0",
        "Accept": "application/json,text/plain,text/html,*/*",
    }
    if json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)

    request = Request(url, data=payload, method=method, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            response_headers = {k.lower(): v for k, v in response.headers.items()}
            return response.status, response_headers, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        response_headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, response_headers, body
    except URLError as exc:
        raise RuntimeError(f"Unable to reach {url}: {exc.reason}") from exc


def _artifact_checks() -> list[Check]:
    checks: list[Check] = []
    for relative in REQUIRED_ARTIFACTS:
        exists = (ROOT / relative).exists()
        checks.append(
            Check(
                key=f"artifact:{relative}",
                label=f"Repository artifact: {relative}",
                status="PASS" if exists else "FAIL",
                detail="present" if exists else "missing",
            )
        )
    return checks


def _public_checks(base_url: str) -> list[Check]:
    checks: list[Check] = []

    if not base_url.startswith("https://"):
        checks.append(
            Check(
                key="https",
                label="Production HTTPS",
                status="FAIL",
                detail=f"Base URL must use HTTPS: {base_url}",
            )
        )
        return checks

    probes = (
        ("homepage", "/", "TrafficVerdict"),
        ("privacy", "/privacy/", None),
        ("terms", "/terms/", None),
        ("robots", "/robots.txt", None),
        ("sitemap", "/sitemap.xml", None),
    )
    for key, path, marker in probes:
        try:
            status, _, body = _request(base_url, path)
            ok = status == 200 and (marker is None or marker.lower() in body.lower())
            checks.append(
                Check(
                    key=key,
                    label=f"Public route {path}",
                    status="PASS" if ok else "FAIL",
                    detail=f"HTTP {status}" + ("" if marker is None else f"; contains {marker!r}: {marker.lower() in body.lower()}"),
                )
            )
        except RuntimeError as exc:
            checks.append(Check(key=key, label=f"Public route {path}", status="FAIL", detail=str(exc)))

    try:
        status, headers, body = _request(base_url, "/api/health")
        health_ok = status == 200
        if health_ok:
            try:
                parsed = json.loads(body)
                health_ok = parsed.get("status") == "ok"
            except json.JSONDecodeError:
                health_ok = False
        checks.append(
            Check(
                key="health",
                label="API health",
                status="PASS" if health_ok else "FAIL",
                detail=f"HTTP {status}; body={body[:140]!r}",
            )
        )

        security_expectations = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "referrer-policy": "same-origin",
            "cache-control": "no-store",
        }
        missing = [
            f"{name}={expected}"
            for name, expected in security_expectations.items()
            if expected.lower() not in headers.get(name, "").lower()
        ]
        checks.append(
            Check(
                key="security-headers",
                label="Production API security headers",
                status="PASS" if not missing else "FAIL",
                detail="all expected headers present" if not missing else "missing/mismatched: " + ", ".join(missing),
            )
        )
    except RuntimeError as exc:
        checks.append(Check(key="health", label="API health", status="FAIL", detail=str(exc)))
        checks.append(
            Check(
                key="security-headers",
                label="Production API security headers",
                status="FAIL",
                detail="health endpoint unavailable",
            )
        )

    probe_email = f"trafficverdict-launch-probe-{int(time.time())}@example.com"
    try:
        status, _, body = _request(
            base_url,
            "/api/auth/forgot-password",
            method="POST",
            json_body={"email": probe_email},
            headers={"Origin": base_url.rstrip("/")},
        )
        if status == 202:
            state, detail = "PASS", "password-reset delivery is configured"
        elif status == 503:
            state, detail = "WARN", "password-reset delivery is not configured yet"
        else:
            state, detail = "FAIL", f"unexpected HTTP {status}: {body[:180]}"
        checks.append(
            Check(
                key="password-reset",
                label="Password-reset delivery",
                status=state,
                detail=detail,
                blocking=False,
            )
        )
    except RuntimeError as exc:
        checks.append(
            Check(
                key="password-reset",
                label="Password-reset delivery",
                status="WARN",
                detail=str(exc),
                blocking=False,
            )
        )

    try:
        status, _, _ = _request(
            base_url,
            "/api/auth/forgot-password",
            method="POST",
            json_body={"email": probe_email},
            headers={"Origin": "https://example.com"},
        )
        checks.append(
            Check(
                key="origin-guard",
                label="Cross-origin state-change protection",
                status="PASS" if status == 403 else "FAIL",
                detail=f"foreign Origin returned HTTP {status}",
            )
        )
    except RuntimeError as exc:
        checks.append(Check(key="origin-guard", label="Cross-origin state-change protection", status="FAIL", detail=str(exc)))

    return checks


def _environment_checks(base_url: str) -> list[Check]:
    """Validate values only when launchctl is run inside a configured runtime."""
    checks: list[Check] = []
    env = os.environ

    requirements = (
        ("DATABASE_URL", True),
        ("AUTH_SECRET", True),
        ("CREDENTIAL_ENCRYPTION_SECRET", True),
        ("SYNC_TRIGGER_SECRET", True),
        ("GOOGLE_CLIENT_ID", True),
        ("GOOGLE_CLIENT_SECRET", True),
    )
    any_runtime_env = any(env.get(name) for name, _ in requirements)
    if not any_runtime_env:
        return [
            Check(
                key="runtime-env",
                label="Runtime environment variables",
                status="MANUAL",
                detail="not visible in this shell; verify them in Render",
                blocking=False,
            )
        ]

    for name, blocking in requirements:
        present = bool(env.get(name))
        checks.append(
            Check(
                key=f"env:{name}",
                label=f"Environment: {name}",
                status="PASS" if present else "FAIL",
                detail="configured" if present else "missing",
                blocking=blocking,
            )
        )

    expected_frontend = base_url.rstrip("/")
    frontend_origin = env.get("FRONTEND_ORIGIN", "").rstrip("/")
    checks.append(
        Check(
            key="env:FRONTEND_ORIGIN",
            label="Environment: FRONTEND_ORIGIN",
            status="PASS" if frontend_origin == expected_frontend else "FAIL",
            detail=f"expected {expected_frontend!r}; got {frontend_origin!r}",
        )
    )

    for variable, suffix in (
        ("GOOGLE_REDIRECT_URI", EXPECTED_GOOGLE_REDIRECTS[0]),
        ("GOOGLE_SEARCH_CONSOLE_REDIRECT_URI", EXPECTED_GOOGLE_REDIRECTS[1]),
    ):
        expected = expected_frontend + suffix
        actual = env.get(variable, "")
        checks.append(
            Check(
                key=f"env:{variable}",
                label=f"Environment: {variable}",
                status="PASS" if actual == expected else "FAIL",
                detail=f"expected {expected!r}; got {actual!r}",
            )
        )

    cookie_secure = env.get("COOKIE_SECURE", "").strip().lower()
    checks.append(
        Check(
            key="env:COOKIE_SECURE",
            label="Environment: COOKIE_SECURE",
            status="PASS" if cookie_secure in {"1", "true", "yes", "on"} else "FAIL",
            detail=f"value={cookie_secure!r}",
        )
    )

    provider = env.get("EMAIL_PROVIDER", "auto").strip().lower()
    brevo = bool(env.get("BREVO_API_KEY"))
    resend = bool(env.get("RESEND_API_KEY"))
    sender = bool(env.get("PASSWORD_RESET_FROM_EMAIL"))
    configured = sender and (
        (provider == "brevo" and brevo)
        or (provider == "resend" and resend)
        or (provider in {"", "auto"} and (brevo or resend))
    )
    checks.append(
        Check(
            key="env:email",
            label="Transactional email environment",
            status="PASS" if configured else "WARN",
            detail=f"provider={provider or 'auto'}; sender={'set' if sender else 'missing'}",
            blocking=False,
        )
    )
    return checks


def _manual_actions(base_url: str) -> list[str]:
    root = base_url.rstrip("/")
    return [
        f"Google OAuth client contains {root}{EXPECTED_GOOGLE_REDIRECTS[0]}",
        f"Google OAuth client contains {root}{EXPECTED_GOOGLE_REDIRECTS[1]}",
        "Google Auth Platform publishing status is In production",
        "Render is serving the intended deployment/public-beta commit",
        "GitHub Actions secrets TRAFFICVERDICT_URL and TRAFFICVERDICT_SYNC_TRIGGER_SECRET are configured",
        "Provider onboarding that requires human verification (for example Brevo account/domain verification) is complete",
        "Run a real end-to-end user smoke test before merging to main",
    ]


def _print_human(checks: list[Check], manual_actions: list[str]) -> None:
    icons = {"PASS": "✓", "WARN": "!", "FAIL": "✗", "MANUAL": "•"}
    print("\nTrafficVerdict Launch Doctor\n")
    for check in checks:
        print(f"{icons.get(check.status, '?')} [{check.status:<6}] {check.label}")
        print(f"           {check.detail}")

    blocking_failures = [c for c in checks if c.status == "FAIL" and c.blocking]
    warnings = [c for c in checks if c.status in {"WARN", "MANUAL"}]

    print("\nManual confirmations")
    for action in manual_actions:
        print(f"• {action}")

    print("\nSummary")
    print(f"  PASS:   {sum(c.status == 'PASS' for c in checks)}")
    print(f"  WARN:   {sum(c.status == 'WARN' for c in checks)}")
    print(f"  MANUAL: {sum(c.status == 'MANUAL' for c in checks)}")
    print(f"  FAIL:   {sum(c.status == 'FAIL' for c in checks)}")

    if blocking_failures:
        print("\nNOT READY: blocking launch checks failed.")
    elif warnings:
        print("\nAUTOMATED BLOCKERS CLEARED: finish the manual confirmations/warnings above.")
    else:
        print("\nAUTOMATED CHECKS GREEN: complete the manual confirmations, then launch.")


def _trigger_sync(base_url: str, secret: str) -> int:
    try:
        status, _, body = _request(
            base_url,
            "/api/internal/scheduled-sync",
            method="POST",
            headers={"Authorization": f"Bearer {secret}", "Origin": base_url.rstrip("/")},
            timeout=300.0,
        )
    except RuntimeError as exc:
        print(f"Scheduled sync trigger failed: {exc}", file=sys.stderr)
        return 1

    print(f"Scheduled sync endpoint returned HTTP {status}")
    if body:
        print(body[:1000])
    return 0 if 200 <= status < 300 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TrafficVerdict launch orchestrator and production readiness doctor."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("FRONTEND_ORIGIN", DEFAULT_BASE_URL),
        help=f"Production base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Skip live HTTP checks and only inspect repository/runtime configuration.",
    )
    parser.add_argument(
        "--trigger-scheduled-sync",
        action="store_true",
        help="Call the protected scheduled-sync endpoint after checks.",
    )
    parser.add_argument(
        "--sync-secret",
        default=os.environ.get("SYNC_TRIGGER_SECRET", ""),
        help="Scheduled-sync bearer secret; defaults to SYNC_TRIGGER_SECRET.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    checks = _artifact_checks()
    checks.extend(_environment_checks(base_url))
    if not args.no_live:
        checks.extend(_public_checks(base_url))

    manual_actions = _manual_actions(base_url)

    if args.json:
        print(
            json.dumps(
                {
                    "base_url": base_url,
                    "checks": [asdict(c) for c in checks],
                    "manual_actions": manual_actions,
                    "blocking_failures": [
                        c.key for c in checks if c.status == "FAIL" and c.blocking
                    ],
                },
                indent=2,
            )
        )
    else:
        _print_human(checks, manual_actions)

    if args.trigger_scheduled_sync:
        if not args.sync_secret:
            print(
                "\nCannot trigger scheduled sync: provide --sync-secret or SYNC_TRIGGER_SECRET.",
                file=sys.stderr,
            )
            return 2
        sync_result = _trigger_sync(base_url, args.sync_secret)
        if sync_result:
            return sync_result

    return 1 if any(c.status == "FAIL" and c.blocking for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
