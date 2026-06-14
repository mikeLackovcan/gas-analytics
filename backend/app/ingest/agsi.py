"""GIE AGSI+ ingest. Storage fullness per country and per facility.

Docs: https://agsi.gie.eu/api
Auth: x-key header (free API key from GIE).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.agsi")

COUNTRIES = ["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES", "SK", "HU", "RO", "BG", "DK", "HR", "LV", "PT", "UK"]


def _headers() -> dict[str, str]:
    return {"x-key": settings.agsi_api_key} if settings.agsi_api_key else {}


def fetch_country_day(country: str, day: date) -> dict | None:
    url = settings.agsi_base_url
    params = {"country": country, "date": day.isoformat(), "size": 60}
    try:
        return get_json(url, params=params, headers=_headers())
    except Exception as e:
        log.warning("agsi %s %s failed: %s", country, day, e)
        return None


def upsert_country_day(country: str, day: date, payload: dict) -> int:
    """Persist AGSI country row. NOTE: AGSI `consumption` is a seasonal AVERAGE
    estimate, not actual day-by-day demand (verified: same value repeats across
    consecutive days). Stored for reference / seasonal baseline only — daily
    demand nowcast comes from mass balance (`/api/balance/country`)."""
    rows = payload.get("data") or []
    if not rows:
        return 0
    r = rows[0]
    init_schema()
    with conn_ctx() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO storage_country_daily VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                day, country,
                _f(r.get("full")),
                _f(r.get("gasInStorage")),
                _f(r.get("workingGasVolume")),
                _f(r.get("injection")),
                _f(r.get("withdrawal")),
                _f(r.get("netWithdrawal")),
                _f(r.get("consumption")),  # seasonal avg — not actual daily
                _f(r.get("trend")),
            ),
        )
    return 1


def _f(v) -> float | None:
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def run(days_back: int = 7, day_from: date | None = None, day_to: date | None = None) -> int:
    today = date.today()
    if day_from and day_to:
        start, end = day_from, day_to
    else:
        start = today - timedelta(days=days_back)
        end = today - timedelta(days=1)
    n = 0
    d = start
    while d <= end:
        for country in COUNTRIES:
            p = fetch_country_day(country, d)
            if p is None:
                continue
            save_raw("agsi", f"{country}_{d.isoformat()}", p, dt=d)
            n += upsert_country_day(country, d, p)
        d += timedelta(days=1)
    log.info("agsi ingested %d country-days (%s..%s)", n, start, end)
    return n


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_", help="YYYY-MM-DD")
    p.add_argument("--to", dest="to_", help="YYYY-MM-DD")
    p.add_argument("--days", type=int, default=7)
    a = p.parse_args()
    if a.from_ and a.to_:
        run(day_from=date.fromisoformat(a.from_), day_to=date.fromisoformat(a.to_))
    else:
        run(days_back=a.days)
