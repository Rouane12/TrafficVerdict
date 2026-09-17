from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SOURCES = ("google_analytics", "google_search_console", "cloudflare")

SOURCE_META: dict[str, dict[str, Any]] = {
    "google_analytics": {
        "label": "Google Analytics",
        "expected_lag_days": 2,
        "timezone": "site",
    },
    "google_search_console": {
        "label": "Search Console",
        "expected_lag_days": 4,
        "timezone": "America/Los_Angeles",
    },
    "cloudflare": {
        "label": "Cloudflare",
        "expected_lag_days": 2,
        "timezone": "UTC",
    },
}


def _as_date(value: date | datetime | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def canonical_date(value: date | datetime | str | None) -> str | None:
    parsed = _as_date(value)
    return parsed.isoformat() if parsed else None


def normalize_hostname(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    parsed = urlsplit(raw if "://" in raw else f"//{raw}")
    hostname = parsed.hostname or raw.split("/", 1)[0].split(":", 1)[0]
    hostname = hostname.strip().rstrip(".").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    try:
        return hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return hostname


def normalize_path(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return "/"

    if "://" in raw or raw.startswith("//"):
        path = urlsplit(raw).path
    else:
        path = raw.split("#", 1)[0].split("?", 1)[0]
    if not path.startswith("/"):
        path = f"/{path}"
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def normalize_url(value: str | None) -> dict[str, Any]:
    raw = (value or "").strip()
    parsed = urlsplit(raw if "://" in raw else f"//{raw}") if raw else None
    hostname = normalize_hostname(parsed.hostname if parsed and parsed.hostname else "")
    path = normalize_path(parsed.path if parsed and parsed.hostname else raw)
    canonical_url = f"https://{hostname}{path}" if hostname else path
    return {
        "original": raw,
        "hostname": hostname or None,
        "path": path,
        "canonical_url": canonical_url,
    }


def _validated_timezone(value: str | None) -> tuple[str, bool]:
    candidate = (value or "UTC").strip() or "UTC"
    try:
        ZoneInfo(candidate)
        return candidate, True
    except ZoneInfoNotFoundError:
        return "UTC", False


def _source_timezone(source: str, site_timezone: str) -> str:
    configured = SOURCE_META[source]["timezone"]
    return site_timezone if configured == "site" else str(configured)


def _normalize_daily_rows(source: str, breakdowns: dict[str, Any]) -> list[dict[str, Any]]:
    raw_rows = breakdowns.get("daily") if isinstance(breakdowns, dict) else []
    rows: list[dict[str, Any]] = []
    for raw in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(raw, dict):
            continue
        day = canonical_date(raw.get("date"))
        if not day:
            continue
        row = {"date": day}
        for key, value in raw.items():
            if key != "date":
                row[key] = value
        rows.append(row)
    rows.sort(key=lambda item: item["date"])
    return rows


def _normalize_breakdowns(source: str, breakdowns: dict[str, Any], site_hostname: str) -> dict[str, Any]:
    result: dict[str, Any] = {"daily": _normalize_daily_rows(source, breakdowns)}
    if source != "google_search_console":
        return result

    top_queries = breakdowns.get("top_queries") if isinstance(breakdowns, dict) else []
    if isinstance(top_queries, list):
        result["top_queries"] = [dict(item) for item in top_queries if isinstance(item, dict)]

    top_pages = breakdowns.get("top_pages") if isinstance(breakdowns, dict) else []
    normalized_pages: list[dict[str, Any]] = []
    if isinstance(top_pages, list):
        for item in top_pages:
            if not isinstance(item, dict):
                continue
            normalized = normalize_url(str(item.get("page") or ""))
            enriched = dict(item)
            enriched["canonical_hostname"] = normalized["hostname"]
            enriched["canonical_path"] = normalized["path"]
            enriched["canonical_url"] = normalized["canonical_url"]
            enriched["matches_site_hostname"] = normalized["hostname"] == site_hostname if normalized["hostname"] else None
            normalized_pages.append(enriched)
    result["top_pages"] = normalized_pages
    return result


def _missing_dates(start: date, end: date, daily: list[dict[str, Any]]) -> list[str]:
    present = {str(item.get("date")) for item in daily}
    missing: list[str] = []
    cursor = start
    while cursor <= end:
        key = cursor.isoformat()
        if key not in present:
            missing.append(key)
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return missing


def _canonical_window(snapshot_map: dict[str, dict[str, Any] | None]) -> tuple[date, date] | None:
    periods: list[tuple[date, date]] = []
    for source in SOURCES:
        snapshot = snapshot_map.get(source)
        if not snapshot:
            continue
        start = _as_date(snapshot.get("period_start"))
        end = _as_date(snapshot.get("period_end"))
        if start and end:
            periods.append((start, end))
    if not periods:
        return None
    start = max(item[0] for item in periods)
    end = min(item[1] for item in periods)
    return (start, end) if start <= end else None


def _requested_window(
    available_window: tuple[date, date] | None,
    requested_days: int | None,
) -> tuple[date, date] | None:
    if available_window is None or requested_days is None:
        return available_window

    days = max(int(requested_days), 1)
    available_start, available_end = available_window
    requested_start = available_end - timedelta(days=days - 1)
    return max(available_start, requested_start), available_end


def _rows_in_window(daily: list[dict[str, Any]], window: tuple[date, date] | None) -> list[dict[str, Any]]:
    if window is None:
        return []
    start, end = window
    selected: list[dict[str, Any]] = []
    for row in daily:
        row_date = _as_date(row.get("date"))
        if row_date and start <= row_date <= end:
            selected.append(row)
    return selected


def _number(row: dict[str, Any], key: str) -> float:
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def _aggregate_canonical_metrics(
    source: str,
    snapshot: dict[str, Any],
    daily: list[dict[str, Any]],
    window: tuple[date, date] | None,
) -> dict[str, Any]:
    native_start = _as_date(snapshot.get("period_start"))
    native_end = _as_date(snapshot.get("period_end"))
    summary = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    rows = _rows_in_window(daily, window)
    exact_window = bool(window and native_start == window[0] and native_end == window[1])

    if source == "google_analytics":
        if not rows:
            return dict(summary) if exact_window else {}
        return {
            "active_users": summary.get("active_users") if exact_window else None,
            "sessions": int(round(sum(_number(row, "sessions") for row in rows))),
            "views": int(round(sum(_number(row, "screenPageViews") for row in rows))),
            "engaged_sessions": int(round(sum(_number(row, "engagedSessions") for row in rows))),
        }

    if source == "google_search_console":
        if not rows:
            return dict(summary) if exact_window else {}
        clicks = sum(_number(row, "clicks") for row in rows)
        impressions = sum(_number(row, "impressions") for row in rows)
        weighted_position = sum(_number(row, "position") * _number(row, "impressions") for row in rows)
        return {
            "clicks": int(round(clicks)),
            "impressions": int(round(impressions)),
            "ctr": clicks / impressions if impressions else 0.0,
            "average_position": weighted_position / impressions if impressions else 0.0,
        }

    if source == "cloudflare":
        if not rows:
            return dict(summary) if exact_window else {}
        return {
            "requests": int(round(sum(_number(row, "requests") for row in rows))),
            "visits": int(round(sum(_number(row, "visits") for row in rows))),
            "data_transfer_bytes": int(round(sum(_number(row, "data_transfer_bytes") for row in rows))),
            "sample_interval": max((_number(row, "sample_interval") for row in rows), default=1.0),
        }

    return dict(summary)


def _dimension_value(source: str, metric: str, value: Any, semantic: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return {"source": source, "metric": metric, "value": value, "semantic": semantic}


def _dimensions(source_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    ga = source_results.get("google_analytics", {}).get("canonical_metrics", {})
    gsc = source_results.get("google_search_console", {}).get("canonical_metrics", {})
    cf = source_results.get("cloudflare", {}).get("canonical_metrics", {})

    definitions = [
        {
            "key": "visit_like_activity",
            "label": "Visit-like activity",
            "comparison_mode": "contextual_not_equivalent",
            "note": "GA4 sessions and Cloudflare visits are related traffic-presence signals, but they use different counting rules and must not be treated as the same metric.",
            "values": [
                _dimension_value("google_analytics", "sessions", ga.get("sessions"), "client-measured sessions"),
                _dimension_value("cloudflare", "visits", cf.get("visits"), "edge-estimated visits"),
            ],
        },
        {
            "key": "page_request_activity",
            "label": "Page/request activity",
            "comparison_mode": "contextual_not_equivalent",
            "note": "GA4 views are browser analytics events; Cloudflare requests are edge HTTP requests. They are useful together but are not directly comparable counts.",
            "values": [
                _dimension_value("google_analytics", "views", ga.get("views"), "analytics page/screen views"),
                _dimension_value("cloudflare", "requests", cf.get("requests"), "edge HTTP requests"),
            ],
        },
        {
            "key": "search_discovery",
            "label": "Search discovery",
            "comparison_mode": "source_specific",
            "note": "Search Console describes Google Search exposure and clicks, not total site traffic.",
            "values": [
                _dimension_value("google_search_console", "clicks", gsc.get("clicks"), "Google Search clicks"),
                _dimension_value("google_search_console", "impressions", gsc.get("impressions"), "Google Search impressions"),
            ],
        },
    ]

    for definition in definitions:
        definition["values"] = [value for value in definition["values"] if value is not None]
    return definitions


def normalize_site_evidence(
    *,
    site_id: str,
    site_domain: str,
    site_timezone: str,
    snapshots: dict[str, dict[str, Any] | None],
    connection_states: dict[str, str] | None = None,
    last_synced_at: dict[str, str | None] | None = None,
    as_of_date: date,
    requested_days: int | None = None,
) -> dict[str, Any]:
    canonical_timezone, timezone_valid = _validated_timezone(site_timezone)
    hostname = normalize_hostname(site_domain)
    connection_states = connection_states or {}
    last_synced_at = last_synced_at or {}
    available_window = _canonical_window(snapshots)
    window = _requested_window(available_window, requested_days)
    warnings: list[str] = []

    if not timezone_valid:
        warnings.append(f"Site timezone '{site_timezone}' is invalid; normalization fell back to UTC.")
    if available_window is None and any(snapshots.get(source) for source in SOURCES):
        warnings.append("Available source snapshots do not share an overlapping date window.")
    if requested_days is not None and available_window is not None and window != available_window:
        warnings.append(
            "The selected date range is calculated from synced daily series. Provider aggregate breakdowns such as Search Console top pages remain scoped to the full synced snapshot and are excluded from date-specific coverage diagnostics."
        )

    source_results: dict[str, dict[str, Any]] = {}
    for source in SOURCES:
        meta = SOURCE_META[source]
        snapshot = snapshots.get(source)
        connection_state = connection_states.get(source, "disconnected")
        basis_timezone = _source_timezone(source, canonical_timezone)

        if not snapshot:
            availability = "connected_missing_snapshot" if connection_state == "connected" else "missing"
            source_results[source] = {
                "source": source,
                "label": meta["label"],
                "connection_state": connection_state,
                "availability": availability,
                "native_period_start": None,
                "native_period_end": None,
                "freshness": {
                    "state": "missing",
                    "data_lag_days": None,
                    "expected_lag_days": meta["expected_lag_days"],
                    "delayed": False,
                },
                "date_alignment": {
                    "source_timezone": basis_timezone,
                    "target_timezone": canonical_timezone,
                    "mode": "no_data",
                },
                "metrics": {},
                "canonical_metrics": {},
                "normalized_breakdowns": {"daily": []},
                "missing_dates": [],
                "last_synced_at": last_synced_at.get(source),
            }
            warnings.append(f"{meta['label']} has no snapshot available for normalization.")
            continue

        native_start = _as_date(snapshot.get("period_start"))
        native_end = _as_date(snapshot.get("period_end"))
        daily = _normalize_daily_rows(
            source,
            snapshot.get("breakdowns") if isinstance(snapshot.get("breakdowns"), dict) else {},
        )
        normalized_breakdowns = _normalize_breakdowns(
            source,
            snapshot.get("breakdowns") if isinstance(snapshot.get("breakdowns"), dict) else {},
            hostname,
        )
        normalized_breakdowns["daily"] = _rows_in_window(
            normalized_breakdowns.get("daily", []),
            window,
        )
        if requested_days is not None and available_window is not None and window != available_window:
            normalized_breakdowns.pop("top_pages", None)
            normalized_breakdowns.pop("top_queries", None)
        lag_days = max((as_of_date - native_end).days, 0) if native_end else None
        delayed = lag_days is not None and lag_days > int(meta["expected_lag_days"])
        if connection_state != "connected":
            freshness_state = "historical"
        else:
            freshness_state = "delayed" if delayed else "fresh"

        alignment_mode = "native_day"
        if basis_timezone != canonical_timezone:
            alignment_mode = "date_label_only"
            warnings.append(
                f"{meta['label']} uses {basis_timezone} day boundaries while the site uses {canonical_timezone}; date labels are normalized without inventing rebinned counts."
            )
        if delayed:
            warnings.append(f"{meta['label']} data is {lag_days} days behind the normalization date.")

        missing = (
            _missing_dates(window[0], window[1], normalized_breakdowns["daily"])
            if window and normalized_breakdowns["daily"]
            else []
        )
        source_results[source] = {
            "source": source,
            "label": meta["label"],
            "connection_state": connection_state,
            "availability": "available",
            "native_period_start": native_start.isoformat() if native_start else None,
            "native_period_end": native_end.isoformat() if native_end else None,
            "freshness": {
                "state": freshness_state,
                "data_lag_days": lag_days,
                "expected_lag_days": meta["expected_lag_days"],
                "delayed": delayed,
            },
            "date_alignment": {
                "source_timezone": basis_timezone,
                "target_timezone": canonical_timezone,
                "mode": alignment_mode,
            },
            "metrics": dict(snapshot.get("metrics") or {}),
            "canonical_metrics": _aggregate_canonical_metrics(source, snapshot, daily, window),
            "normalized_breakdowns": normalized_breakdowns,
            "missing_dates": missing,
            "last_synced_at": last_synced_at.get(source),
        }

    canonical_window = None
    if window:
        available_days = (
            (available_window[1] - available_window[0]).days + 1
            if available_window
            else (window[1] - window[0]).days + 1
        )
        canonical_window = {
            "start": window[0].isoformat(),
            "end": window[1].isoformat(),
            "days": (window[1] - window[0]).days + 1,
            "rule": (
                "requested_last_n_days_within_available_overlap"
                if requested_days is not None
                else "intersection_of_available_source_periods"
            ),
            "requested_days": requested_days,
            "available_days": available_days,
        }

    return {
        "site_id": site_id,
        "canonical_hostname": hostname,
        "canonical_timezone": canonical_timezone,
        "as_of_date": as_of_date.isoformat(),
        "canonical_window": canonical_window,
        "sources": source_results,
        "dimensions": _dimensions(source_results),
        "warnings": sorted(set(warnings)),
        "normalization_version": "1.0.0",
    }
