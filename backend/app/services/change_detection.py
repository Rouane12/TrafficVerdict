from __future__ import annotations

from typing import Any

SOURCE_SPECS: dict[str, dict[str, str]] = {
    "google_analytics": {
        "label": "Google Analytics",
        "primary_metric": "sessions",
        "primary_label": "sessions",
    },
    "google_search_console": {
        "label": "Search Console",
        "primary_metric": "clicks",
        "primary_label": "clicks",
    },
    "cloudflare": {
        "label": "Cloudflare",
        "primary_metric": "visits",
        "primary_label": "visits",
    },
}

MIN_BASELINES = {
    "google_analytics": 5.0,
    "google_search_console": 3.0,
    "cloudflare": 25.0,
}


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _rows(source: dict[str, Any]) -> list[dict[str, Any]]:
    breakdowns = source.get("normalized_breakdowns") if isinstance(source, dict) else {}
    rows = breakdowns.get("daily") if isinstance(breakdowns, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return ((current - previous) / previous) * 100.0


def _direction(percent: float | None) -> str:
    if percent is None:
        return "unknown"
    if percent >= 20:
        return "up"
    if percent <= -20:
        return "down"
    return "stable"


def _period_sum(rows: list[dict[str, Any]], metric: str, start: int, end: int) -> float:
    return sum(_number(row.get(metric)) for row in rows[start:end])


def _period_record(source_key: str, rows: list[dict[str, Any]], *, days: int) -> dict[str, Any] | None:
    spec = SOURCE_SPECS[source_key]
    metric = spec["primary_metric"]
    if len(rows) < days * 2:
        return None

    previous_rows = rows[-(days * 2):-days]
    current_rows = rows[-days:]
    previous = sum(_number(row.get(metric)) for row in previous_rows)
    current = sum(_number(row.get(metric)) for row in current_rows)
    percent = _change(current, previous)

    return {
        "source": source_key,
        "label": spec["label"],
        "metric": spec["primary_label"],
        "previous": round(previous, 2),
        "current": round(current, 2),
        "change_percent": round(percent, 1) if percent is not None else None,
        "direction": _direction(percent),
        "previous_start": previous_rows[0].get("date"),
        "previous_end": previous_rows[-1].get("date"),
        "current_start": current_rows[0].get("date"),
        "current_end": current_rows[-1].get("date"),
        "baseline_sufficient": previous >= MIN_BASELINES[source_key],
    }


def _daily_record(source_key: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(rows) < 2:
        return None
    spec = SOURCE_SPECS[source_key]
    metric = spec["primary_metric"]
    previous = _number(rows[-2].get(metric))
    current = _number(rows[-1].get(metric))
    percent = _change(current, previous)
    return {
        "source": source_key,
        "label": spec["label"],
        "metric": spec["primary_label"],
        "previous": round(previous, 2),
        "current": round(current, 2),
        "change_percent": round(percent, 1) if percent is not None else None,
        "direction": _direction(percent),
        "previous_date": rows[-2].get("date"),
        "current_date": rows[-1].get("date"),
    }


def build_change_detection(normalized: dict[str, Any]) -> dict[str, Any]:
    sources = normalized.get("sources") if isinstance(normalized.get("sources"), dict) else {}
    weekly: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []

    for key in SOURCE_SPECS:
        source = sources.get(key, {})
        if source.get("availability") != "available":
            continue
        rows = _rows(source)
        weekly_record = _period_record(key, rows, days=7)
        daily_record = _daily_record(key, rows)
        if weekly_record:
            weekly.append(weekly_record)
        if daily_record:
            daily.append(daily_record)

    anomalies: list[dict[str, Any]] = []
    weekly_by_source = {item["source"]: item for item in weekly}

    for item in weekly:
        pct = item["change_percent"]
        if (
            pct is not None
            and item["baseline_sufficient"]
            and abs(pct) >= 60
        ):
            anomalies.append({
                "anomaly_type": "large_source_change",
                "severity": "info",
                "title": f"{item['label']} {item['metric']} changed sharply",
                "explanation": (
                    f"{item['label']} {item['metric']} changed {pct:+.1f}% versus the previous 7-day period. "
                    "This is a measured change, not a claim about its cause."
                ),
                "confidence": "high",
                "source_evidence": [item],
            })

    ga = weekly_by_source.get("google_analytics")
    cf = weekly_by_source.get("cloudflare")
    if (
        ga
        and cf
        and ga["change_percent"] is not None
        and cf["change_percent"] is not None
        and ga["baseline_sufficient"]
        and cf["baseline_sufficient"]
    ):
        divergence = abs(float(ga["change_percent"]) - float(cf["change_percent"]))
        if divergence >= 50 and (
            abs(float(ga["change_percent"])) >= 40
            or abs(float(cf["change_percent"])) >= 40
        ):
            anomalies.append({
                "anomaly_type": "cross_source_divergence",
                "severity": "warning",
                "title": "GA4 and Cloudflare changed in different ways",
                "explanation": (
                    "Browser-measured sessions and Cloudflare visit estimates moved very differently compared with the previous week. "
                    "That can indicate a measurement or traffic-mix change, but TrafficVerdict does not assign a cause without stronger evidence."
                ),
                "confidence": "medium",
                "source_evidence": [ga, cf],
            })

    cf_source = sources.get("cloudflare", {})
    cf_rows = _rows(cf_source)
    if len(cf_rows) >= 14:
        current_requests = _period_sum(cf_rows, "requests", -7, len(cf_rows))
        previous_requests = _period_sum(cf_rows, "requests", -14, -7)
        request_change = _change(current_requests, previous_requests)
        cf_visits = weekly_by_source.get("cloudflare")
        if (
            request_change is not None
            and cf_visits
            and cf_visits["change_percent"] is not None
            and previous_requests >= 100
            and abs(request_change) >= 80
            and abs(float(cf_visits["change_percent"])) <= 30
        ):
            anomalies.append({
                "anomaly_type": "network_activity_divergence",
                "severity": "warning",
                "title": "Cloudflare requests changed much more than visits",
                "explanation": (
                    f"Cloudflare requests changed {request_change:+.1f}% while visit estimates changed only "
                    f"{float(cf_visits['change_percent']):+.1f}%. This can reflect assets, crawlers, retries, API traffic, "
                    "or other network activity, so it should not be treated as visitor growth by itself."
                ),
                "confidence": "medium",
                "source_evidence": [{
                    "source": "cloudflare",
                    "previous_requests": round(previous_requests, 2),
                    "current_requests": round(current_requests, 2),
                    "request_change_percent": round(request_change, 1),
                    "visit_change_percent": cf_visits["change_percent"],
                }],
            })

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    anomalies.sort(key=lambda item: (severity_rank.get(item["severity"], 9), item["title"]))

    if not weekly:
        summary = "Not enough synced daily history exists yet for a week-over-week comparison."
        state = "insufficient_history"
    elif anomalies:
        summary = f"TrafficVerdict found {len(anomalies)} notable change{'' if len(anomalies) == 1 else 's'} in the latest comparison."
        state = "changes_detected"
    else:
        summary = "No major week-over-week divergence was detected in the available synced history."
        state = "stable"

    canonical_window = normalized.get("canonical_window")
    return {
        "site_id": normalized.get("site_id"),
        "state": state,
        "summary": summary,
        "analysis_window": canonical_window,
        "weekly_comparisons": weekly,
        "daily_comparisons": daily,
        "anomalies": anomalies,
        "change_detection_version": "1.0.0",
    }
