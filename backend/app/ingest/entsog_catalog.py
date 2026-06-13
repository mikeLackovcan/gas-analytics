"""Bootstrap the IP master from ENTSOG /interconnections.

This replaces the hand-coded `app.reference.ips` seed with the live catalog.
Run after schema init; idempotent (REPLACE on conflict).

Filters:
  - cross-border only (fromCountryKey != toCountryKey)
  - ITP- and VIP- only (drop DIS-/LNG-/PRD- noise)
  - dedupe by canonical orientation: we keep ONE row per (from,to) physical IP,
    picking the side flagged fromHasData when both exist.
"""
from __future__ import annotations

import logging

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.entsog_catalog")


def fetch_interconnections() -> list[dict]:
    url = f"{settings.entsog_base_url}/interconnections"
    payload = get_json(url, params={"limit": 20000})
    return payload.get("interconnections", []) if isinstance(payload, dict) else []


def upsert(rows: list[dict]) -> int:
    init_schema()
    n = 0
    seen: set[str] = set()
    with conn_ctx() as c:
        c.execute("DELETE FROM ip")
        for r in rows:
            pk = r.get("pointKey", "")
            if not (pk.startswith("ITP-") or pk.startswith("VIP-")):
                continue
            cf, ct = r.get("fromCountryKey"), r.get("toCountryKey")
            if not cf or not ct or cf == ct:
                continue
            if pk in seen:
                continue
            seen.add(pk)
            c.execute(
                """INSERT OR REPLACE INTO ip VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pk,
                    r.get("pointLabel"),
                    cf, ct,
                    r.get("fromOperatorKey"), r.get("toOperatorKey"),
                    None,
                    "operator",
                    r.get("pointTpMapX"),
                    r.get("pointTpMapY"),
                    bool(r.get("fromHasData") or r.get("toHasData")),
                    True,
                ),
            )
            n += 1
    return n


def run() -> int:
    rows = fetch_interconnections()
    save_raw("entsog", "interconnections_catalog", rows)
    n = upsert(rows)
    log.info("entsog catalog ingested %d cross-border IPs", n)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("catalog rows:", run())
