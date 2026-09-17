from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx

from app.core.credentials import decrypt_secret
from app.models.connection import Connection

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
CLOUDFLARE_GRAPHQL_URL = f"{CLOUDFLARE_API_BASE}/graphql"


class CloudflareError(RuntimeError):
    pass


def _error_message(payload: Any, status_code: int) -> str:
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict) and first.get("message"):
                return str(first["message"])
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            first = messages[0]
            if isinstance(first, dict) and first.get("message"):
                return str(first["message"])
    return f"Cloudflare API request failed with status {status_code}"


async def _api_json(
    method: str,
    url: str,
    api_token: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, headers=headers, params=params, json=json_body)

    try:
        payload = response.json()
    except ValueError as exc:
        raise CloudflareError(f"Cloudflare returned a non-JSON response ({response.status_code})") from exc

    if not response.is_success:
        raise CloudflareError(_error_message(payload, response.status_code))

    if isinstance(payload, dict) and payload.get("success") is False:
        raise CloudflareError(_error_message(payload, response.status_code))

    return payload


async def list_cloudflare_zones(api_token: str) -> list[dict[str, str | None]]:
    if not api_token:
        raise CloudflareError("Enter a Cloudflare API token")

    zones: list[dict[str, str | None]] = []
    page = 1
    while True:
        payload = await _api_json(
            "GET",
            f"{CLOUDFLARE_API_BASE}/zones",
            api_token,
            params={"page": page, "per_page": 50, "direction": "asc"},
        )
        for item in payload.get("result", []):
            zone_id = str(item.get("id") or "")
            name = str(item.get("name") or "")
            if not zone_id or not name:
                continue
            account = item.get("account") if isinstance(item.get("account"), dict) else {}
            zones.append(
                {
                    "zone_id": zone_id,
                    "name": name,
                    "status": str(item.get("status") or "unknown"),
                    "account_name": str(account.get("name")) if account.get("name") else None,
                }
            )

        result_info = payload.get("result_info") if isinstance(payload.get("result_info"), dict) else {}
        total_pages = int(result_info.get("total_pages") or page)
        if page >= total_pages:
            break
        page += 1
        if page > 20:
            break

    return sorted(zones, key=lambda item: str(item["name"]).lower())


def connection_api_token(connection: Connection) -> str:
    token = decrypt_secret(connection.encrypted_access_token)
    if not token:
        raise CloudflareError("Cloudflare connection needs a new API token")
    return token


async def list_connection_zones(connection: Connection) -> list[dict[str, str | None]]:
    return await list_cloudflare_zones(connection_api_token(connection))


CLOUDFLARE_TRAFFIC_QUERY = """
query TrafficVerdictCloudflare($zoneTag: string, $start: Time, $end: Time) {
  viewer {
    zones(filter: {zoneTag: $zoneTag}) {
      summary: httpRequestsAdaptiveGroups(
        limit: 1
        filter: {datetime_geq: $start, datetime_lt: $end, requestSource: "eyeball"}
      ) {
        count
        avg { sampleInterval }
        sum { visits edgeResponseBytes }
      }
    }
  }
}
"""


async def _graphql(api_token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = await _api_json(
        "POST",
        CLOUDFLARE_GRAPHQL_URL,
        api_token,
        json_body={"query": query, "variables": variables},
    )
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        raise CloudflareError(_error_message(payload, 200))
    return payload


def _iso_utc(day: date) -> str:
    return datetime.combine(day, time.min, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _row_values(row: dict[str, Any] | None) -> tuple[int, int, int, float]:
    row = row or {}
    sums = row.get("sum") if isinstance(row.get("sum"), dict) else {}
    avg = row.get("avg") if isinstance(row.get("avg"), dict) else {}
    return (
        int(round(float(row.get("count") or 0))),
        int(round(float(sums.get("visits") or 0))),
        int(round(float(sums.get("edgeResponseBytes") or 0))),
        float(avg.get("sampleInterval") or 1),
    )


def _zone_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    viewer = data.get("viewer") if isinstance(data.get("viewer"), dict) else {}
    zones = viewer.get("zones") if isinstance(viewer.get("zones"), list) else []
    if not zones or not isinstance(zones[0], dict):
        return None
    return zones[0]


async def fetch_cloudflare_snapshot(connection: Connection) -> dict[str, Any]:
    if not connection.external_resource_id:
        raise CloudflareError("Select a Cloudflare zone before syncing")

    api_token = connection_api_token(connection)
    end_exclusive = date.today()
    start_date = end_exclusive - timedelta(days=28)
    end_date = end_exclusive - timedelta(days=1)

    # Some zones/plans limit adaptive analytics to one day per query. Query each
    # completed day separately, store that day's aggregate directly, and then sum
    # those same daily rows. This keeps the headline and normalized evidence on
    # one consistent data source instead of mixing daily hourly-groups with a
    # different summary aggregate.
    requests = 0
    visits = 0
    data_transfer_bytes = 0
    sample_interval = 1.0
    daily: list[dict[str, Any]] = []

    current_day = start_date
    while current_day < end_exclusive:
        next_day = current_day + timedelta(days=1)
        payload = await _graphql(
            api_token,
            CLOUDFLARE_TRAFFIC_QUERY,
            {
                "zoneTag": connection.external_resource_id,
                "start": _iso_utc(current_day),
                "end": _iso_utc(next_day),
            },
        )

        zone = _zone_from_payload(payload)
        if zone is None:
            raise CloudflareError(f"Cloudflare returned no zone analytics container for {current_day.isoformat()}")

        summary_rows = zone.get("summary", []) if isinstance(zone.get("summary"), list) else []
        day_requests, day_visits, day_bytes, day_sample_interval = _row_values(summary_rows[0] if summary_rows else None)

        daily.append(
            {
                "date": current_day.isoformat(),
                "requests": day_requests,
                "visits": day_visits,
                "data_transfer_bytes": day_bytes,
                "sample_interval": day_sample_interval,
            }
        )
        requests += day_requests
        visits += day_visits
        data_transfer_bytes += day_bytes
        sample_interval = max(sample_interval, day_sample_interval)
        current_day = next_day

    return {
        "period_start": start_date,
        "period_end": end_date,
        "metrics": {
            "requests": requests,
            "visits": visits,
            "data_transfer_bytes": data_transfer_bytes,
            "sample_interval": sample_interval,
        },
        "breakdowns": {"daily": daily, "daily_complete": True},
    }
