"""APScheduler wiring. Runs inside the FastAPI process.

Jobs:
  agsi/alsi  09:15 CET  (GIE publishes ~08:30 CET for D-1)
  entsog     every 4h   (provisional intraday → confirmed D+1)
  entsoe     every 1h
  hdd        00:30 + 12:30 UTC (after ECMWF 00z/12z run posts)
  nowcast    09:30 CET  (after AGSI lands)
  prices     09:00 CET  (after user drops CSV)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_agsi():
    from .ingest.agsi import run
    run(days_back=2)


def _job_alsi():
    from .ingest.alsi import run
    run(days_back=2)


def _job_entsog():
    from .ingest.entsog import run
    run(days_back=2)


def _job_entsoe():
    from .ingest.entsoe import BZ_EIC, run as run_e
    for c in BZ_EIC:
        try:
            run_e(c, days_back=2)
        except Exception as e:
            log.warning("entsoe %s failed: %s", c, e)


def _job_hdd():
    from .ingest.hdd import run_history, run_forecast
    from .reference.cities import CITIES
    today = date.today()
    countries = list(CITIES.keys())
    try:
        run_history(countries, today - timedelta(days=5), today - timedelta(days=2))
    except Exception as e:
        log.warning("hdd history failed: %s", e)
    try:
        run_forecast(countries, days_ahead=15)
    except Exception as e:
        log.warning("hdd forecast failed: %s", e)


def _job_nowcast():
    from .ingest.demand_nowcast import run
    run(days_back=5)


def _job_prices():
    from .ingest.prices_csv import run
    run()


def _job_forecast():
    """Refit LDZ + persist D+1..D+10 forecast per country."""
    from .forecast.ldz import fit_and_forecast_all
    fit_and_forecast_all(
        countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
        train_years=3,
        horizon_days=10,
    )


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler(timezone="Europe/Berlin")
    # GIE feeds — DST-aware Europe/Berlin
    sched.add_job(_job_agsi, CronTrigger(hour=9, minute=15), id="agsi", replace_existing=True, max_instances=1)
    sched.add_job(_job_alsi, CronTrigger(hour=9, minute=20), id="alsi", replace_existing=True, max_instances=1)
    sched.add_job(_job_prices, CronTrigger(hour=9, minute=0), id="prices", replace_existing=True, max_instances=1)
    sched.add_job(_job_nowcast, CronTrigger(hour=9, minute=35), id="nowcast", replace_existing=True, max_instances=1)
    sched.add_job(_job_forecast, CronTrigger(hour=10, minute=0), id="forecast", replace_existing=True, max_instances=1)
    # ENTSOG: every 4h
    sched.add_job(_job_entsog, IntervalTrigger(hours=4), id="entsog", replace_existing=True, max_instances=1)
    # ENTSO-E: hourly at :10
    sched.add_job(_job_entsoe, CronTrigger(minute=10), id="entsoe", replace_existing=True, max_instances=1)
    # HDD after ECMWF cycles (UTC). Using CronTrigger in CET; rounding to local equivalent.
    sched.add_job(_job_hdd, CronTrigger(hour="2,14", minute=30), id="hdd", replace_existing=True, max_instances=1)
    sched.start()
    _scheduler = sched
    log.info("scheduler started: jobs=%s", [j.id for j in sched.get_jobs()])
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
