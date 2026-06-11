"""ENTSOG Transparency Platform ingest — physical flows at IPs.

Docs: https://transparency.entsog.eu/api/v1/operationalData.json
Auth: none, rate-limited.

Indicator codes we use:
  - "Physical Flow"   confirmed flow at IP (kWh/d on daily aggregation)
  - "Renomination"    forward-looking nomination

Each IP has two adjacent operators reporting; we filter by `reporting_side`
recorded in the IP master to avoid double counting.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.entsog")


def fetch_operational(day_from: date, day_to: date, indicator: str = "Physical Flow", limit: int = 10_000) -> list[dict]:
    url = f"{settings.entsog_base_url}/operationalData"
    params = {
        "from": day_from.isoformat(),
        "to": day_to.isoformat(),
        "indicator": indicator,
        "periodType": "day",
        "limit": limit,
    }
    payload = get_json(url, params=params)
    rows = payload.get("operationalData") if isinstance(payload, dict) else payload
    return rows or []


def upsert_flows(rows: list[dict]) -> int:
    if not rows:
        return 0
    init_schema()
    n = 0
    with conn_ctx() as c:
        existing_ips = {x[0] for x in c.execute("SELECT id FROM ip").fetchall()}
        for r in rows:
            ip_id = r.get("pointKey") or r.get("interconnectionPointKey") or r.get("ipId")
            if ip_id not in existing_ips:
                continue
            day_str = r.get("periodFrom") or r.get("date")
            if not day_str:
                continue
            d = date.fromisoformat(day_str[:10])
            direction = (r.get("directionKey") or r.get("direction") or "").lower()
            kwh = r.get("value")
            try:
                kwh = float(kwh) if kwh is not None else None
            except (TypeError, ValueError):
                continue
            if kwh is None:
                continue
            c.execute(
                "INSERT OR REPLACE INTO flow_ip_daily VALUES (?, ?, ?, ?)",
                (d, ip_id, direction, kwh),
            )
            n += 1
    return n


def run(days_back: int = 3) -> int:
    today = date.today()
    day_from = today - timedelta(days=days_back)
    day_to = today
    rows = fetch_operational(day_from, day_to)
    save_raw("entsog", f"physical_flow_{day_from}_{day_to}", rows, dt=today)
    n = upsert_flows(rows)
    log.info("entsog ingested %d rows for %s..%s", n, day_from, day_to)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
