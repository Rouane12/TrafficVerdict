from __future__ import annotations

from collections import defaultdict
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
      hourly: httpRequestsAdaptiveGroups(
        limit: 1000
        orderBy: [datetimeHour_ASC]
        filter: {datetime_geq: $start, datetime_lt: $end, requestSource: "eyeball"}
      ) {
        count
        avg { sampleInterval }
        sum { visits edgeResponseBytes }
        dimensions { datetimeHour }
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


async def fetch_cloudflare_snapshot(connection: Connection) -> dict[str, Any]:
    if not connection.external_resource_id:
        raise CloudflareError("Select a Cloudflare zone before syncing")

    api_token = connection_api_token(connection)
    end_exclusive = date.today()
    start_date = end_exclusive - timedelta(days=28)
    end_date = end_exclusive - timedelta(days=1)

    payload = await _graphql(
        api_token,
        CLOUDFLARE_TRAFFIC_QUERY,
        {
            "zoneTag": connection.external_resource_id,
            "start": _iso_utc(start_date),
            "end": _iso_utc(end_exclusive),
        },
    )

    viewer = payload.get("data", {}).get("viewer", {}) if isinstance(payload.get("data"), dict) else {}
    zones = viewer.get("zones", []) if isinstance(viewer, dict) else []
    if not zones:
        raise CloudflareError("Cloudflare returned no analytics for the selected zone")

    zone = zones[0] if isinstance(zones[0], dict) else {}
    summary_rows = zone.get("summary", []) if isinstance(zone.get("summary"), list) else []
    hourly_rows = zone.get("hourly", []) if isinstance(zone.get("hourly"), list) else []

    requests, visits, data_transfer_bytes, sample_interval = _row_values(
        summary_rows[0] if summary_rows else None
    )

    daily_map: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"requests": 0, "visits": 0, "data_transfer_bytes": 0, "sample_intervals": []}
    )
    for row in hourly_rows:
        if not isinstance(row, dict):
            continue
        dimensions = row.get("dimensions") if isinstance(row.get("dimensions"), dict) else {}
        stamp = str(dimensions.get("datetimeHour") or "")
        if len(stamp) < 10:
            continue
        day_key = stamp[:10]
        row_requests, row_visits, row_bytes, row_sample_interval = _row_values(row)
        bucket = daily_map[day_key]
        bucket["requests"] += row_requests
        bucket["visits"] += row_visits
        bucket["data_transfer_bytes"] += row_bytes
        bucket["sample_intervals"].append(row_sample_interval)

    daily: list[dict[str, Any]] = []
    for day_key in sorted(daily_map):
        bucket = daily_map[day_key]
        samples = bucket.pop("sample_intervals")
        daily.append(
            {
                "date": day_key,
                "requests": bucket["requests"],
                "visits": bucket["visits"],
                "data_transfer_bytes": bucket["data_transfer_bytes"],
                "sample_interval": sum(samples) / len(samples) if samples else 1,
            }
        )

    # If the summary group is absent, fall back to the sum of the hourly groups.
    if not summary_rows and daily:
        requests = sum(item["requests"] for item in daily)
        visits = sum(item["visits"] for item in daily)
        data_transfer_bytes = sum(item["data_transfer_bytes"] for item in daily)
        sample_interval = max((item["sample_interval"] for item in daily), default=1)

    return {
        "period_start": start_date,
        "period_end": end_date,
        "metrics": {
            "requests": requests,
            "visits": visits,
            "data_transfer_bytes": data_transfer_bytes,
            "sample_interval": sample_interval,
        },
        "breakdowns": {"daily": daily},
    }
