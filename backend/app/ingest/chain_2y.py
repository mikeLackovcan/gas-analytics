"""One-shot chain: ENTSOG -> HDD -> demand_nowcast -> LDZ fit + backtest.

Assumes AGSI + ALSI 2y backfills already done. Run after ALSI completes.
"""
from __future__ import annotations

import logging
import time
from datetime import date

DAY_FROM = date(2024, 6, 1)
DAY_TO = date(2026, 6, 13)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    t0 = time.time()

    log = logging.getLogger("chain")

    from . import entsog
    log.info("=== ENTSOG 2y backfill ===")
    n = entsog.run(day_from=DAY_FROM, day_to=DAY_TO, chunk_days=30)
    log.info("ENTSOG: %d rows in %.1fs", n, time.time() - t0)

    from . import hdd
    from ..reference.cities import CITIES
    t1 = time.time()
    log.info("=== HDD 2y history (era5) ===")
    n = hdd.run_history(list(CITIES.keys()), DAY_FROM, DAY_TO)
    log.info("HDD: %d rows in %.1fs", n, time.time() - t1)

    from . import demand_nowcast
    t2 = time.time()
    log.info("=== demand_nowcast over 2y ===")
    n = demand_nowcast.run(day_from=DAY_FROM, day_to=DAY_TO)
    log.info("nowcast: %d rows in %.1fs", n, time.time() - t2)

    from ..forecast.ldz import fit_and_forecast_all
    t3 = time.time()
    log.info("=== LDZ fit + forecast persist ===")
    res = fit_and_forecast_all(
        countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
        train_years=2, horizon_days=10,
    )
    log.info("LDZ done in %.1fs, %d countries", time.time() - t3, len(res))

    from ..forecast.backtest import run_all as backtest_run
    t4 = time.time()
    log.info("=== Backtest last 6mo ===")
    bt = backtest_run(
        countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
        months_test=6, train_years=2,
    )
    log.info("Backtest done in %.1fs, %d countries", time.time() - t4, len(bt))

    log.info("=== CHAIN COMPLETE in %.1fs ===", time.time() - t0)


if __name__ == "__main__":
    main()
