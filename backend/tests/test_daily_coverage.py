from datetime import date

from app.services.google_analytics import _complete_daily_rows as complete_ga4_daily
from app.services.google_search_console import _complete_daily_rows as complete_gsc_daily


def test_ga4_daily_coverage_zero_fills_omitted_dates() -> None:
    rows = [
        {
            "date": "2026-09-02",
            "activeUsers": 3,
            "sessions": 4,
            "screenPageViews": 5,
            "engagedSessions": 2,
        }
    ]
    completed = complete_ga4_daily(date(2026, 9, 1), date(2026, 9, 3), rows)

    assert [row["date"] for row in completed] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert completed[0]["sessions"] == 0
    assert completed[1]["sessions"] == 4
    assert completed[2]["screenPageViews"] == 0


def test_search_console_daily_coverage_zero_fills_no_search_days() -> None:
    rows = [
        {
            "date": "2026-09-02",
            "clicks": 1,
            "impressions": 20,
            "ctr": 0.05,
            "position": 8.0,
        }
    ]
    completed = complete_gsc_daily(date(2026, 9, 1), date(2026, 9, 3), rows)

    assert [row["date"] for row in completed] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert completed[0]["clicks"] == 0
    assert completed[1]["impressions"] == 20
    assert completed[2]["position"] == 0.0
