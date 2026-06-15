"""Pull `--years` of history (default 3) for all sources. Idempotent.

Usage:
    python -m app.ingest.backfill_all --years 3
    python -m app.ingest.backfill_all --from 2023-01-01 --to 2026-06-01
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from . import agsi, alsi, entsog, entsoe
from ..reference.seed import seed_all, bootstrap_ips, bootstrap_storage


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, default=3)
    p.add_argument("--from", dest="from_", help="YYYY-MM-DD")
    p.add_argument("--to", dest="to_", help="YYYY-MM-DD")
    p.add_argument("--skip", nargs="*", default=[], help="sources to skip: agsi alsi entsog entsoe")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    today = date.today()
    if a.from_ and a.to_:
        df, dt = date.fromisoformat(a.from_), date.fromisoformat(a.to_)
    else:
        df = today - timedelta(days=365 * a.years)
        dt = today - timedelta(days=1)

    seed_all()
    bootstrap_ips()
    bootstrap_storage()

    if "agsi" not in a.skip:
        agsi.run(day_from=df, day_to=dt)
    if "alsi" not in a.skip:
        alsi.run(day_from=df, day_to=dt)
    if "entsog" not in a.skip:
        entsog.run(day_from=df, day_to=dt, chunk_days=30)
    if "entsoe" not in a.skip:
        from .entsoe import BZ_EIC, run as run_e
        for c in BZ_EIC:
            cur = df
            while cur < dt:
                chunk_end = min(cur + timedelta(days=30), dt)
                run_e(c, day_from=cur, day_to=chunk_end)
                cur = chunk_end
    if "hdd" not in a.skip:
        from .hdd import run_history
        from ..reference.cities import CITIES
        run_history(list(CITIES.keys()), df, dt)
    if "nowcast" not in a.skip:
        from .demand_nowcast import run as run_nw
        run_nw(day_from=df, day_to=dt)
    if "forecast" not in a.skip:
        from ..forecast.ldz import fit_and_forecast_all
        fit_and_forecast_all(
            countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
            train_years=2, horizon_days=10,
        )


if __name__ == "__main__":
    main()
