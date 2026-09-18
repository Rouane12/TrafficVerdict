from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

AS_OF = date(2026, 9, 17)
START = date(2026, 8, 20)
END = date(2026, 9, 16)


def _daily(start: date, end: date, values: dict[str, int | float]) -> list[dict]:
    rows = []
    cursor = start
    while cursor <= end:
        rows.append({"date": cursor.isoformat(), **values})
        cursor += timedelta(days=1)
    return rows


def normal_snapshots() -> dict:
    return {
        "google_analytics": {
            "period_start": START,
            "period_end": END,
            "metrics": {"active_users": 114, "sessions": 121, "views": 173, "engaged_sessions": 75},
            "breakdowns": {"daily": _daily(START, END, {"activeUsers": 5, "sessions": 6, "screenPageViews": 8, "engagedSessions": 4})},
        },
        "google_search_console": {
            "period_start": START,
            "period_end": date(2026, 9, 14),
            "metrics": {"clicks": 7, "impressions": 477, "ctr": 0.015, "average_position": 11.7},
            "breakdowns": {
                "daily": _daily(START, date(2026, 9, 14), {"clicks": 1, "impressions": 20, "ctr": 0.05, "position": 12}),
                "top_pages": [{"page": "https://www.neuralcritic.net/reviews/?utm_source=x#top", "clicks": 4, "impressions": 90, "ctr": 0.04, "position": 8}],
                "top_queries": [{"query": "neural critic", "clicks": 3, "impressions": 30, "ctr": 0.1, "position": 4}],
            },
        },
        "cloudflare": {
            "period_start": START,
            "period_end": END,
            "metrics": {"requests": 181264, "visits": 5332, "data_transfer_bytes": 1492501135, "sample_interval": 4.5},
            "breakdowns": {"daily": _daily(START, END, {"requests": 6500, "visits": 190, "data_transfer_bytes": 53000000, "sample_interval": 4.5})},
        },
    }


def cases() -> dict[str, dict]:
    normal = normal_snapshots()

    crawler_spike = deepcopy(normal)
    crawler_spike["cloudflare"]["metrics"]["requests"] = 900000
    # Put the spike on the last day shared by all three sources (GSC ends on 2026-09-14)
    # so reconciliation evaluates it inside the canonical comparison window.
    crawler_spike["cloudflare"]["breakdowns"]["daily"][-3]["requests"] = 500000

    ga4_outage = deepcopy(normal)
    ga4_outage["google_analytics"] = None

    gsc_only_spike = deepcopy(normal)
    gsc_only_spike["google_search_console"]["metrics"].update({"clicks": 500, "impressions": 25000})
    gsc_only_spike["google_search_console"]["breakdowns"]["daily"][-1].update({"clicks": 450, "impressions": 20000})

    partial_path_tracking = deepcopy(normal)
    partial_path_tracking["google_search_console"]["breakdowns"]["top_pages"].append(
        {"page": "https://neuralcritic.net/news//nintendo/?ref=home#section", "clicks": 2, "impressions": 50, "ctr": 0.04, "position": 9}
    )

    missing_cloudflare = deepcopy(normal)
    missing_cloudflare["cloudflare"] = None

    timezone_mismatch = deepcopy(normal)

    return {
        "normal_site": {"timezone": "Africa/Casablanca", "snapshots": normal},
        "large_crawler_spike": {"timezone": "Africa/Casablanca", "snapshots": crawler_spike},
        "ga4_outage": {"timezone": "Africa/Casablanca", "snapshots": ga4_outage},
        "gsc_only_spike": {"timezone": "Africa/Casablanca", "snapshots": gsc_only_spike},
        "partial_path_tracking": {"timezone": "Africa/Casablanca", "snapshots": partial_path_tracking},
        "missing_cloudflare_data": {"timezone": "Africa/Casablanca", "snapshots": missing_cloudflare},
        "timezone_mismatch": {"timezone": "Pacific/Auckland", "snapshots": timezone_mismatch},
    }
