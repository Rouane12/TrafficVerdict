from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse
from uuid import UUID

import httpx
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.credentials import decrypt_secret, encrypt_secret
from app.models.connection import Connection

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SEARCH_CONSOLE_BASE = "https://www.googleapis.com/webmasters/v3"


class SearchConsoleError(RuntimeError):
    pass


def search_console_oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def create_oauth_state(user_id: UUID, site_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "google_search_console_oauth_state",
        "sub": str(user_id),
        "site_id": str(site_id),
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_oauth_state(state: str) -> tuple[UUID, UUID]:
    try:
        payload = jwt.decode(state, settings.auth_secret, algorithms=["HS256"])
        if payload.get("typ") != "google_search_console_oauth_state":
            raise ValueError("Invalid OAuth state type")
        return UUID(payload["sub"]), UUID(payload["site_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise SearchConsoleError("Invalid or expired Search Console OAuth state") from exc


def build_authorization_url(user_id: UUID, site_id: UUID) -> str:
    if not search_console_oauth_configured():
        raise SearchConsoleError("Google OAuth is not configured")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_search_console_redirect_uri,
        "response_type": "code",
        "scope": settings.google_search_console_scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": create_oauth_state(user_id, site_id),
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def _extract_google_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"Google API request failed with status {response.status_code}"

    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(error, str):
            return str(body.get("error_description") or error)
    return f"Google API request failed with status {response.status_code}"


async def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, data=data)
    if not response.is_success:
        raise SearchConsoleError(_extract_google_error(response))
    return response.json()


async def exchange_authorization_code(code: str) -> dict[str, Any]:
    return await _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_search_console_redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def apply_token_payload(connection: Connection, payload: dict[str, Any]) -> None:
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise SearchConsoleError("Google did not return an access token")

    connection.encrypted_access_token = encrypt_secret(access_token)

    refresh_token = payload.get("refresh_token")
    if isinstance(refresh_token, str) and refresh_token:
        connection.encrypted_refresh_token = encrypt_secret(refresh_token)

    expires_in = int(payload.get("expires_in") or 3600)
    connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 60))

    scope = payload.get("scope")
    if isinstance(scope, str):
        connection.granted_scopes = scope


async def _refresh_access_token(connection: Connection, db: Session) -> str:
    refresh_token = decrypt_secret(connection.encrypted_refresh_token)
    if not refresh_token:
        raise SearchConsoleError("Search Console connection needs to be authorized again")

    payload = await _post_form(
        GOOGLE_TOKEN_URL,
        {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    apply_token_payload(connection, payload)
    db.add(connection)
    db.commit()
    return decrypt_secret(connection.encrypted_access_token) or ""


async def get_access_token(connection: Connection, db: Session) -> str:
    access_token = decrypt_secret(connection.encrypted_access_token)
    expires_at = connection.token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if access_token and expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=30):
        return access_token
    return await _refresh_access_token(connection, db)


async def _authorized_json(
    method: str,
    url: str,
    access_token: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=headers, json=json_body)
    if not response.is_success:
        raise SearchConsoleError(_extract_google_error(response))
    return response.json()


def _display_name(site_url: str) -> str:
    if site_url.startswith("sc-domain:"):
        return site_url.removeprefix("sc-domain:")
    parsed = urlparse(site_url)
    return parsed.hostname or site_url


async def list_search_console_sites(connection: Connection, db: Session) -> list[dict[str, str]]:
    access_token = await get_access_token(connection, db)
    payload = await _authorized_json("GET", f"{SEARCH_CONSOLE_BASE}/sites", access_token)

    sites: list[dict[str, str]] = []
    for item in payload.get("siteEntry", []):
        site_url = str(item.get("siteUrl") or "")
        permission_level = str(item.get("permissionLevel") or "")
        if not site_url or permission_level == "siteUnverifiedUser":
            continue
        sites.append(
            {
                "site_url": site_url,
                "display_name": _display_name(site_url),
                "permission_level": permission_level,
            }
        )
    return sorted(sites, key=lambda item: item["display_name"].lower())


def _row_metrics(row: dict[str, Any] | None) -> dict[str, float]:
    row = row or {}
    return {
        "clicks": float(row.get("clicks") or 0),
        "impressions": float(row.get("impressions") or 0),
        "ctr": float(row.get("ctr") or 0),
        "position": float(row.get("position") or 0),
    }


async def _search_analytics_query(
    access_token: str,
    site_url: str,
    *,
    start_date: date,
    end_date: date,
    dimensions: list[str] | None = None,
    row_limit: int = 1000,
) -> dict[str, Any]:
    encoded_site = quote(site_url, safe="")
    body: dict[str, Any] = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "type": "web",
        "dataState": "final",
        "rowLimit": row_limit,
    }
    if dimensions:
        body["dimensions"] = dimensions
    return await _authorized_json(
        "POST",
        f"{SEARCH_CONSOLE_BASE}/sites/{encoded_site}/searchAnalytics/query",
        access_token,
        json_body=body,
    )


def _breakdown_rows(payload: dict[str, Any], key_name: str, *, limit: int = 25) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in payload.get("rows", [])[:limit]:
        keys = row.get("keys") or []
        metrics = _row_metrics(row)
        result.append(
            {
                key_name: str(keys[0]) if keys else "",
                "clicks": int(round(metrics["clicks"])),
                "impressions": int(round(metrics["impressions"])),
                "ctr": metrics["ctr"],
                "position": metrics["position"],
            }
        )
    return result


def _complete_daily_rows(start_date: date, end_date: date, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = {str(row.get("date")): row for row in rows if row.get("date")}
    completed: list[dict[str, Any]] = []
    cursor = start_date
    while cursor <= end_date:
        key = cursor.isoformat()
        completed.append(
            by_date.get(
                key,
                {
                    "date": key,
                    "clicks": 0,
                    "impressions": 0,
                    "ctr": 0.0,
                    "position": 0.0,
                },
            )
        )
        cursor += timedelta(days=1)
    return completed


async def fetch_search_console_snapshot(connection: Connection, db: Session) -> dict[str, Any]:
    if not connection.external_resource_id:
        raise SearchConsoleError("Select a Search Console property before syncing")

    access_token = await get_access_token(connection, db)
    site_url = connection.external_resource_id

    # Search Console data has processing latency. Probe finalized daily rows first,
    # then use the newest finalized date as the end of a stable 28-day window.
    today = date.today()
    probe_payload = await _search_analytics_query(
        access_token,
        site_url,
        start_date=today - timedelta(days=45),
        end_date=today - timedelta(days=1),
        dimensions=["date"],
        row_limit=1000,
    )
    finalized_dates: list[date] = []
    for row in probe_payload.get("rows", []):
        keys = row.get("keys") or []
        if not keys:
            continue
        try:
            finalized_dates.append(date.fromisoformat(str(keys[0])))
        except ValueError:
            continue

    end_date = max(finalized_dates) if finalized_dates else today - timedelta(days=3)
    start_date = end_date - timedelta(days=27)

    summary_payload = await _search_analytics_query(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        row_limit=1,
    )
    summary_rows = summary_payload.get("rows", [])
    summary = _row_metrics(summary_rows[0] if summary_rows else None)

    daily_payload = await _search_analytics_query(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["date"],
        row_limit=1000,
    )
    query_payload = await _search_analytics_query(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["query"],
        row_limit=100,
    )
    page_payload = await _search_analytics_query(
        access_token,
        site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=100,
    )

    daily = _breakdown_rows(daily_payload, "date", limit=1000)
    daily = _complete_daily_rows(start_date, end_date, daily)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "metrics": {
            "clicks": int(round(summary["clicks"])),
            "impressions": int(round(summary["impressions"])),
            "ctr": summary["ctr"],
            "average_position": summary["position"],
        },
        "breakdowns": {
            "daily": daily,
            "daily_complete": True,
            "top_queries": _breakdown_rows(query_payload, "query"),
            "top_pages": _breakdown_rows(page_payload, "page"),
        },
    }
