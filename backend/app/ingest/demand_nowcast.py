"""Compute mass-balance demand nowcast per country and persist to demand_country_daily.

  demand = Σ(entries) − Σ(exits) + withdrawal − injection + lng_sendout − production_domestic

Run after AGSI / ALSI / ENTSOG ingests have landed. Only writes rows where we
have at least one flow side and one storage side (otherwise the value is too
unreliable to publish).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ..db import conn_ctx, init_schema

log = logging.getLogger("ingest.demand_nowcast")

# Countries we have a demand model intent for.
COUNTRIES = ["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"]


def compute_country_day(country: str, day: date) -> float | None:
    """Mass-balance net cross-border by operator country attribution.

    Each ENTSOG row carries an operator_key like 'DE-TSO-0001'. The first two
    chars identify the operator's country. For country C we sum across operators
    in C: entries (gas entering C's grid) − exits (gas leaving). This avoids
    the double-counting that arises if we attribute by IP country_from/_to
    (each IP gets reported by both adjacent operators)."""
    prefix = f"{country}-"
    with conn_ctx() as c:
        flow = c.execute(
            """
            SELECT
                SUM(CASE WHEN f.direction='entry' THEN f.kwh ELSE 0 END) / 1e6,
                SUM(CASE WHEN f.direction='exit'  THEN f.kwh ELSE 0 END) / 1e6
            FROM flow_ip_daily f
            WHERE f.date = ? AND f.operator_key LIKE ?
            """,
            (day, prefix + "%"),
        ).fetchone()
        entries_gwh, exits_gwh = flow or (None, None)
        st = c.execute(
            "SELECT injection_gwh, withdrawal_gwh FROM storage_country_daily WHERE country = ? AND date = ?",
            (country, day),
        ).fetchone()
        inj, wdr = st or (None, None)
        lng = c.execute(
            "SELECT sendout_gwh FROM lng_terminal_daily WHERE terminal_id = ? AND date = ?",
            (f"{country}-AGG", day),
        ).fetchone()
        lng_so = lng[0] if lng else None

    if entries_gwh is None and exits_gwh is None and inj is None:
        return None
    return (
        (entries_gwh or 0) - (exits_gwh or 0)
        + (wdr or 0) - (inj or 0)
        + (lng_so or 0)
    )


def run(days_back: int = 7, day_from: date | None = None, day_to: date | None = None) -> int:
    init_schema()
    today = date.today()
    if day_from and day_to:
        start, end = day_from, day_to
    else:
        start = today - timedelta(days=days_back)
        end = today - timedelta(days=1)
    n = 0
    with conn_ctx() as c:
        d = start
        while d <= end:
            for country in COUNTRIES:
                val = compute_country_day(country, d)
                if val is None:
                    continue
                c.execute(
                    "INSERT OR REPLACE INTO demand_country_daily VALUES (?, ?, ?, ?)",
                    (d, country, val, "mass-balance-v0.1"),
                )
                n += 1
            d += timedelta(days=1)
    log.info("demand_nowcast wrote %d rows (%s..%s)", n, start, end)
    return n


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_")
    p.add_argument("--to", dest="to_")
    p.add_argument("--days", type=int, default=7)
    a = p.parse_args()
    if a.from_ and a.to_:
        run(day_from=date.fromisoformat(a.from_), day_to=date.fromisoformat(a.to_))
    else:
        run(days_back=a.days)
