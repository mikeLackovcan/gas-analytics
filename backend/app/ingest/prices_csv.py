"""Daily hub-price ingest via manual CSV drop.

Why CSV: every free public TTF/THE/PEG endpoint we evaluated is either blocked
(Yahoo/yfinance), paywalled (ICE/EEX direct), or fragile to scrape. A trader
already has terminal access to clean EOD settles — the cheapest reliable path
is to drop CSVs from that workflow.

Expected CSV shape (header-row, comma-separated):
    date,hub,contract,settle_eur_mwh
    2026-06-13,TTF,M+1,35.42
    2026-06-13,TTF,Cal27,38.10
    2026-06-13,THE,M+1,35.85
    2026-06-13,PEG,M+1,36.20

Files in `data/prices/manual/*.csv` are processed; processed files are moved
to `data/prices/manual/_loaded/` so re-runs are idempotent.
"""
from __future__ import annotations

import csv
import logging
import shutil
from datetime import date
from pathlib import Path

from ..config import settings
from ..db import conn_ctx, init_schema

log = logging.getLogger("ingest.prices_csv")


def _manual_dir() -> Path:
    p = settings.data_dir / "prices" / "manual"
    p.mkdir(parents=True, exist_ok=True)
    (p / "_loaded").mkdir(exist_ok=True)
    return p


def load_file(fp: Path) -> int:
    init_schema()
    n = 0
    with conn_ctx() as c, fp.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                d = date.fromisoformat(row["date"].strip())
                hub = row["hub"].strip().upper()
                contract = (row.get("contract") or "M+1").strip()
                settle = float(row["settle_eur_mwh"])
            except (KeyError, ValueError) as e:
                log.warning("%s: bad row %s (%s)", fp.name, row, e)
                continue
            c.execute(
                "INSERT OR REPLACE INTO price_daily VALUES (?, ?, ?, ?, ?)",
                (d, hub, settle, contract, "csv-manual"),
            )
            n += 1
    return n


def run() -> int:
    folder = _manual_dir()
    total = 0
    for fp in sorted(folder.glob("*.csv")):
        if fp.parent.name == "_loaded":
            continue
        n = load_file(fp)
        total += n
        if n > 0:
            shutil.move(str(fp), folder / "_loaded" / fp.name)
            log.info("loaded %d rows from %s -> _loaded/", n, fp.name)
    log.info("prices_csv ingested %d total rows", total)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("rows:", run())
