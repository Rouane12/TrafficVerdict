from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.credentials import decrypt_secret, encrypt_secret
from app.models.connection import Connection

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_ADMIN_BASE = "https://analyticsadmin.googleapis.com/v1beta"
GOOGLE_DATA_BASE = "https://analyticsdata.googleapis.com/v1beta"


class GoogleAnalyticsError(RuntimeError):
    pass


def google_oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def create_oauth_state(user_id: UUID, site_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "google_analytics_oauth_state",
        "sub": str(user_id),
        "site_id": str(site_id),
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm="HS256")


def decode_oauth_state(state: str) -> tuple[UUID, UUID]:
    try:
        payload = jwt.decode(state, settings.auth_secret, algorithms=["HS256"])
        if payload.get("typ") != "google_analytics_oauth_state":
            raise ValueError("Invalid OAuth state type")
        return UUID(payload["sub"]), UUID(payload["site_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise GoogleAnalyticsError("Invalid or expired Google OAuth state") from exc


def build_authorization_url(user_id: UUID, site_id: UUID) -> str:
    if not google_oauth_configured():
        raise GoogleAnalyticsError("Google OAuth is not configured")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": settings.google_analytics_scope,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
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
            description = body.get("error_description")
            return str(description or error)
    return f"Google API request failed with status {response.status_code}"


async def _post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, data=data)
    if not response.is_success:
        raise GoogleAnalyticsError(_extract_google_error(response))
    return response.json()


async def exchange_authorization_code(code: str) -> dict[str, Any]:
    return await _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def apply_token_payload(connection: Connection, payload: dict[str, Any]) -> None:
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleAnalyticsError("Google did not return an access token")

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
        raise GoogleAnalyticsError("Google connection needs to be authorized again")

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
    params: dict[str, str | int] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=headers, params=params, json=json_body)
    if not response.is_success:
        raise GoogleAnalyticsError(_extract_google_error(response))
    return response.json()


async def list_ga4_properties(connection: Connection, db: Session) -> list[dict[str, str]]:
    access_token = await get_access_token(connection, db)
    properties: list[dict[str, str]] = []
    page_token: str | None = None

    while True:
        params: dict[str, str | int] = {"pageSize": 200}
        if page_token:
            params["pageToken"] = page_token
        payload = await _authorized_json(
            "GET",
            f"{GOOGLE_ADMIN_BASE}/accountSummaries",
            access_token,
            params=params,
        )

        for account in payload.get("accountSummaries", []):
            account_id = str(account.get("account") or "")
            account_name = str(account.get("displayName") or account_id)
            for prop in account.get("propertySummaries", []):
                property_name = str(prop.get("property") or "")
                if not property_name:
                    continue
                properties.append(
                    {
                        "property_id": property_name,
                        "property_name": str(prop.get("displayName") or property_name),
                        "account_id": account_id,
                        "account_name": account_name,
                    }
                )

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return properties


def _metric_values(payload: dict[str, Any]) -> dict[str, int]:
    headers = [str(item.get("name")) for item in payload.get("metricHeaders", [])]
    rows = payload.get("rows", [])
    if not rows:
        return {name: 0 for name in headers}

    values = rows[0].get("metricValues", [])
    result: dict[str, int] = {}
    for name, item in zip(headers, values):
        try:
            result[name] = int(float(item.get("value", "0")))
        except (TypeError, ValueError):
            result[name] = 0
    return result


def _format_ga_date(value: str) -> str:
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


async def fetch_ga4_snapshot(connection: Connection, db: Session) -> dict[str, Any]:
    if not connection.external_resource_id:
        raise GoogleAnalyticsError("Select a Google Analytics property before syncing")

    access_token = await get_access_token(connection, db)
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=27)
    property_name = connection.external_resource_id
    report_url = f"{GOOGLE_DATA_BASE}/{property_name}:runReport"
    metrics = [
        {"name": "activeUsers"},
        {"name": "sessions"},
        {"name": "screenPageViews"},
        {"name": "engagedSessions"},
    ]
    date_ranges = [{"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}]

    summary_payload = await _authorized_json(
        "POST",
        report_url,
        access_token,
        json_body={"dateRanges": date_ranges, "metrics": metrics, "returnPropertyQuota": True},
    )
    daily_payload = await _authorized_json(
        "POST",
        report_url,
        access_token,
        json_body={
            "dateRanges": date_ranges,
            "dimensions": [{"name": "date"}],
            "metrics": metrics,
            "orderBys": [{"dimension": {"dimensionName": "date"}}],
            "limit": "100",
        },
    )

    normalized = _metric_values(summary_payload)
    daily: list[dict[str, Any]] = []
    for row in daily_payload.get("rows", []):
        dimension_values = row.get("dimensionValues", [])
        metric_values = row.get("metricValues", [])
        raw_date = str(dimension_values[0].get("value", "")) if dimension_values else ""
        daily_item: dict[str, Any] = {"date": _format_ga_date(raw_date)}
        for name, item in zip([m["name"] for m in metrics], metric_values):
            try:
                daily_item[name] = int(float(item.get("value", "0")))
            except (TypeError, ValueError):
                daily_item[name] = 0
        daily.append(daily_item)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "metrics": {
            "active_users": normalized.get("activeUsers", 0),
            "sessions": normalized.get("sessions", 0),
            "views": normalized.get("screenPageViews", 0),
            "engaged_sessions": normalized.get("engagedSessions", 0),
        },
        "breakdowns": {"daily": daily},
    }


async def revoke_connection_tokens(connection: Connection) -> None:
    token = decrypt_secret(connection.encrypted_refresh_token) or decrypt_secret(connection.encrypted_access_token)
    if not token:
        return
    async with httpx.AsyncClient(timeout=15.0) as client:
        await client.post(GOOGLE_REVOKE_URL, data={"token": token})
