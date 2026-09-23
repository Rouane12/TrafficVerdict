#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

DEFAULT_BASE_URL = "https://trafficverdict.app"


class SmokeFailure(RuntimeError):
    pass


def _request(opener, base_url: str, path: str, *, method: str = "GET", body: dict | None = None):
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "User-Agent": "TrafficVerdict-Production-Auth-Smoke/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        headers["Origin"] = base_url.rstrip("/")

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=30) as response:
            payload = response.read().decode("utf-8", errors="replace")
            return response.status, response.headers, payload
    except HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        return exc.code, exc.headers, payload
    except URLError as exc:
        raise SmokeFailure(f"Unable to reach {url}: {exc.reason}") from exc


def _json(payload: str) -> dict:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"Expected JSON response, received: {payload[:200]!r}") from exc
    if not isinstance(parsed, dict):
        raise SmokeFailure(f"Expected JSON object, received: {type(parsed).__name__}")
    return parsed


def _expect(status: int, expected: int, label: str, payload: str = "") -> None:
    if status != expected:
        raise SmokeFailure(f"{label}: expected HTTP {expected}, got {status}: {payload[:300]}")


def run(base_url: str) -> None:
    cookie_jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))

    nonce = f"{int(time.time())}-{secrets.token_hex(4)}"
    email = f"trafficverdict-smoke+{nonce}@example.com"
    password = f"Smoke-{secrets.token_urlsafe(20)}"
    created = False

    print(f"Testing production authentication at {base_url}")
    print(f"Disposable account: {email}")

    try:
        status, _, payload = _request(
            opener,
            base_url,
            "/api/auth/register",
            method="POST",
            body={"email": email, "password": password, "display_name": "Launch Smoke"},
        )
        _expect(status, 201, "register", payload)
        created = True
        registered = _json(payload)
        if registered.get("email") != email:
            raise SmokeFailure("register: normalized email mismatch")
        print("✓ register")

        session_cookie = next(
            (cookie for cookie in cookie_jar if cookie.name == "trafficverdict_session"),
            None,
        )
        if session_cookie is None:
            raise SmokeFailure("register: session cookie was not stored")
        if not session_cookie.secure:
            raise SmokeFailure("register: production session cookie is not Secure")
        print("✓ secure session cookie")

        status, _, payload = _request(opener, base_url, "/api/auth/me")
        _expect(status, 200, "authenticated /me", payload)
        me = _json(payload)
        if me.get("email") != email:
            raise SmokeFailure("authenticated /me: wrong user returned")
        print("✓ authenticated session restored")

        status, _, payload = _request(opener, base_url, "/api/workspaces")
        _expect(status, 200, "authenticated workspace access", payload)
        print("✓ authenticated dashboard API access")

        status, _, payload = _request(opener, base_url, "/api/auth/logout", method="POST")
        _expect(status, 204, "logout", payload)
        print("✓ logout")

        status, _, payload = _request(opener, base_url, "/api/auth/me")
        _expect(status, 401, "post-logout /me", payload)
        print("✓ logged-out session rejected")

        status, _, payload = _request(
            opener,
            base_url,
            "/api/auth/login",
            method="POST",
            body={"email": email.upper(), "password": password},
        )
        _expect(status, 200, "sign back in", payload)
        print("✓ sign back in")

        status, _, payload = _request(opener, base_url, "/api/auth/me")
        _expect(status, 200, "restored /me", payload)
        restored = _json(payload)
        if restored.get("email") != email:
            raise SmokeFailure("restored /me: wrong user returned")
        print("✓ restored session verified")

        status, _, payload = _request(opener, base_url, "/")
        _expect(status, 200, "signed-in landing page", payload)
        print("✓ signed-in user can visit landing page")

        status, _, payload = _request(opener, base_url, "/api/auth/me")
        _expect(status, 200, "session after landing page", payload)
        after_landing = _json(payload)
        if after_landing.get("email") != email:
            raise SmokeFailure("session after landing page: wrong user returned")
        print("✓ landing page preserves authenticated session")

        status, _, payload = _request(
            opener,
            base_url,
            "/api/auth/account",
            method="DELETE",
            body={"current_password": password, "confirmation": "DELETE"},
        )
        _expect(status, 204, "delete disposable account", payload)
        created = False
        print("✓ disposable account deleted")
    finally:
        if created:
            try:
                _request(
                    opener,
                    base_url,
                    "/api/auth/login",
                    method="POST",
                    body={"email": email, "password": password},
                )
                status, _, _ = _request(
                    opener,
                    base_url,
                    "/api/auth/account",
                    method="DELETE",
                    body={"current_password": password, "confirmation": "DELETE"},
                )
                if status == 204:
                    print("✓ cleanup completed after failure", file=sys.stderr)
            except Exception as cleanup_error:
                print(f"! cleanup could not complete: {cleanup_error}", file=sys.stderr)

    print("\nPRODUCTION AUTH SMOKE PASSED")


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise TrafficVerdict production authentication end to end.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    try:
        run(args.base_url.rstrip("/"))
    except SmokeFailure as exc:
        print(f"PRODUCTION AUTH SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
