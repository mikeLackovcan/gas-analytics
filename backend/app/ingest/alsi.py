"""GIE ALSI ingest. LNG terminal sendout, inventory.

Docs: https://alsi.gie.eu/api
Auth: x-key header (same key as AGSI works on free tier).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.alsi")

# Map ALSI EIC / facility codes to our terminal IDs as we discover them.
# For Phase 1 we ingest by country aggregate; per-terminal mapping table grows over time.
COUNTRIES = ["DE", "NL", "FR", "IT", "ES", "PL", "PT", "BE", "GR", "HR", "LT", "FI", "UK"]


def _headers() -> dict[str, str]:
    key = settings.alsi_api_key or settings.agsi_api_key
    return {"x-key": key} if key else {}


def fetch_country_day(country: str, day: date) -> dict | None:
    url = f"{settings.alsi_base_url}/"
    params = {"country": country, "date": day.isoformat(), "size": 60}
    try:
        return get_json(url, params=params, headers=_headers())
    except Exception as e:
        log.warning("alsi %s %s failed: %s", country, day, e)
        return None


def _f(v):
    try:
        return float(v) if v not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def upsert_country_day(country: str, day: date, payload: dict) -> int:
    """Aggregate country-level row stored under terminal_id=<country>-AGG."""
    rows = payload.get("data") or []
    if not rows:
        return 0
    r = rows[0]
    init_schema()
    with conn_ctx() as c:
        c.execute(
            """
            INSERT OR REPLACE INTO lng_terminal_daily VALUES (?, ?, ?, ?, ?)
            """,
            (
                day,
                f"{country}-AGG",
                _f(r.get("sendOut")),
                _f(r.get("lngInventory")),
                _f(r.get("dtmi")),
            ),
        )
    return 1


def run(days_back: int = 7) -> int:
    today = date.today()
    n = 0
    for back in range(days_back, 0, -1):
        d = today - timedelta(days=back)
        for country in COUNTRIES:
            p = fetch_country_day(country, d)
            if p is None:
                continue
            save_raw("alsi", f"{country}_{d.isoformat()}", p, dt=d)
            n += upsert_country_day(country, d, p)
    log.info("alsi ingested %d country-days", n)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
