"""Bootstrap LNG terminal catalog from ALSI /about.

ALSI free tier returns country aggregates only for series data (same constraint
as AGSI), but /about gives the full LSO → terminal hierarchy with EICs, type
(FSRU/onshore), operator. We use that to replace the hand-coded
`reference/lng_terminals.py` with the authoritative live list.
"""
from __future__ import annotations

import logging

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.alsi_catalog")

_NAME_TO_ISO = {
    "Belgium": "BE", "Croatia": "HR", "Finland": "FI", "France": "FR",
    "Germany": "DE", "Greece": "GR", "Italy": "IT", "Lithuania": "LT",
    "Netherlands": "NL", "Poland": "PL", "Portugal": "PT", "Spain": "ES",
    "United Kingdom": "UK",
}


def fetch_about() -> dict:
    key = settings.alsi_api_key or settings.agsi_api_key
    return get_json(f"{settings.alsi_base_url}/about", headers={"x-key": key} if key else None)


def upsert(payload: dict) -> int:
    init_schema()
    europe = (payload.get("LSO") or {}).get("Europe") or {}
    n = 0
    with conn_ctx() as c:
        c.execute("DELETE FROM lng_terminal")
        for country_name, ops in europe.items():
            iso = _NAME_TO_ISO.get(country_name)
            if not iso:
                continue
            for op in ops or []:
                operator = op.get("short_name") or op.get("name")
                for fac in op.get("facilities") or []:
                    eic = fac.get("eic")
                    if not eic:
                        continue
                    # Capacity / storage values are NOT in /about — set None; can be filled
                    # from per-terminal sendout query or hand-loaded reference factsheets.
                    c.execute(
                        "INSERT OR REPLACE INTO lng_terminal VALUES (?, ?, ?, ?, ?, ?)",
                        (eic, iso, fac.get("name"), None, None, operator),
                    )
                    n += 1
    return n


def run() -> int:
    p = fetch_about()
    save_raw("alsi", "about_catalog", p)
    n = upsert(p)
    log.info("alsi catalog: %d terminals", n)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("terminals:", run())
