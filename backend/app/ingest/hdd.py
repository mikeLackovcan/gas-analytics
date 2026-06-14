"""Population-weighted HDD per country, via Open-Meteo.

Open-Meteo is free, no auth, two endpoints we use:
  - https://archive-api.open-meteo.com/v1/era5            (history → climatology + training)
  - https://api.open-meteo.com/v1/forecast                (D-1..D+15 forecast)

We pull daily mean 2m temperature per city, compute HDD_15.5C = max(0, 15.5 - T),
then weight by city population to get country HDD.

Schema:
  hdd_country_daily(date, country, hdd_pop, source, fcst_run)
  source: 'era5' for historical, 'open-meteo-fcst' for forecast
  fcst_run: UTC datetime of the run that produced this number (today for hist)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from ..config import settings
from ..db import conn_ctx, init_schema
from ..reference.cities import CITIES
from .common import save_raw

log = logging.getLogger("ingest.hdd")

HDD_BASE = 15.5  # °C, EU industry convention


def _hdd(t_c: float) -> float:
    return max(0.0, HDD_BASE - t_c)


def fetch_archive(lat: float, lon: float, day_from: date, day_to: date) -> dict:
    """ERA5 reanalysis history; up to D-2."""
    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": day_from.isoformat(), "end_date": day_to.isoformat(),
        "daily": "temperature_2m_mean",
        "timezone": "UTC",
    }
    with httpx.Client(timeout=60.0) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def fetch_forecast(lat: float, lon: float, days_ahead: int = 15) -> dict:
    """ECMWF-backed forecast; provides past_days + forecast_days."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "daily": "temperature_2m_mean",
        "past_days": 2,
        "forecast_days": days_ahead,
        "timezone": "UTC",
        "models": "ecmwf_ifs025",
    }
    with httpx.Client(timeout=60.0) as c:
        r = c.get(url, params=params)
        r.raise_for_status()
        return r.json()


def _country_hdd_series(country: str, fetch_fn) -> dict[date, float]:
    """fetch_fn(lat, lon) -> {date: temp_c}. Returns {date: weighted HDD}."""
    cities = CITIES.get(country) or []
    if not cities:
        return {}
    total_pop = sum(p for _, _, _, p in cities)
    all_dates: dict[date, float] = {}
    for name, lat, lon, pop in cities:
        try:
            temps = fetch_fn(lat, lon)
        except Exception as e:
            log.warning("hdd fetch %s/%s failed: %s", country, name, e)
            continue
        w = pop / total_pop
        for d, t in temps.items():
            if t is None:
                continue
            all_dates[d] = all_dates.get(d, 0.0) + w * _hdd(t)
    return all_dates


def _parse_daily(payload: dict) -> dict[date, float]:
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    temps = daily.get("temperature_2m_mean") or []
    out: dict[date, float] = {}
    for d, t in zip(dates, temps):
        try:
            out[date.fromisoformat(d)] = float(t) if t is not None else None  # type: ignore[assignment]
        except (TypeError, ValueError):
            continue
    return out


def upsert(country: str, source: str, fcst_run: datetime, series: dict[date, float]) -> int:
    if not series:
        return 0
    init_schema()
    with conn_ctx() as c:
        for d, h in series.items():
            c.execute(
                "INSERT OR REPLACE INTO hdd_country_daily VALUES (?, ?, ?, ?, ?)",
                (d, country, float(h), source, fcst_run),
            )
    return len(series)


def run_history(countries: list[str], day_from: date, day_to: date) -> int:
    """ERA5 backfill for the given countries / dates."""
    run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    total = 0
    for country in countries:
        cities = CITIES.get(country) or []
        if not cities:
            continue
        per_city: list[dict[date, float]] = []
        for name, lat, lon, pop in cities:
            try:
                payload = fetch_archive(lat, lon, day_from, day_to)
                save_raw("open-meteo", f"era5_{country}_{name}_{day_from}_{day_to}", payload, dt=day_to)
            except Exception as e:
                log.warning("era5 %s/%s failed: %s", country, name, e)
                continue
            per_city.append((pop, _parse_daily(payload)))  # type: ignore[arg-type]
        if not per_city:
            continue
        total_pop = sum(p for p, _ in per_city)
        merged: dict[date, float] = {}
        for pop, temps in per_city:
            w = pop / total_pop
            for d, t in temps.items():
                if t is None:
                    continue
                merged[d] = merged.get(d, 0.0) + w * _hdd(t)
        total += upsert(country, "era5", run_ts, merged)
    log.info("hdd era5: %d country-day rows", total)
    return total


def run_forecast(countries: list[str], days_ahead: int = 15) -> int:
    run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    total = 0
    for country in countries:
        cities = CITIES.get(country) or []
        if not cities:
            continue
        per_city: list[tuple[int, dict[date, float]]] = []
        for name, lat, lon, pop in cities:
            try:
                payload = fetch_forecast(lat, lon, days_ahead=days_ahead)
                save_raw("open-meteo", f"fcst_{country}_{name}_{run_ts.date()}", payload, dt=run_ts.date())
            except Exception as e:
                log.warning("forecast %s/%s failed: %s", country, name, e)
                continue
            per_city.append((pop, _parse_daily(payload)))
        if not per_city:
            continue
        total_pop = sum(p for p, _ in per_city)
        merged: dict[date, float] = {}
        for pop, temps in per_city:
            w = pop / total_pop
            for d, t in temps.items():
                if t is None:
                    continue
                merged[d] = merged.get(d, 0.0) + w * _hdd(t)
        total += upsert(country, "open-meteo-fcst", run_ts, merged)
    log.info("hdd forecast: %d country-day rows", total)
    return total


def run(days_back: int = 30, days_ahead: int = 15) -> int:
    today = date.today()
    countries = list(CITIES.keys())
    n_hist = run_history(countries, today - timedelta(days=days_back), today - timedelta(days=2))
    n_fcst = run_forecast(countries, days_ahead=days_ahead)
    return n_hist + n_fcst


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="from_")
    p.add_argument("--to", dest="to_")
    p.add_argument("--days-back", type=int, default=30)
    p.add_argument("--days-ahead", type=int, default=15)
    p.add_argument("--countries", nargs="*")
    a = p.parse_args()
    countries = a.countries or list(CITIES.keys())
    if a.from_ and a.to_:
        run_history(countries, date.fromisoformat(a.from_), date.fromisoformat(a.to_))
    else:
        run(days_back=a.days_back, days_ahead=a.days_ahead)
