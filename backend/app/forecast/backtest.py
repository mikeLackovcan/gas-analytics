"""Walk-forward backtest harness for the LDZ model.

Standard rolling-origin evaluation:
  for each test day t in [start, end]:
    train on [t - train_years, t-1]
    fit, predict t (1-day-ahead, no roll-forward over predictions for D+1 test)
    record (actual, yhat, persistence_y, climatology_y)
  aggregate MAE/RMSE/MAPE + skill vs persistence + skill vs climatology
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from ..db import conn_ctx
from .ldz import _features, _holidays, feature_cols, load_training

log = logging.getLogger("forecast.backtest")


@dataclass
class BacktestResult:
    country: str
    n: int
    mae: float
    rmse: float
    mape: float
    persistence_mae: float
    climatology_mae: float
    skill_vs_persistence: float
    skill_vs_climatology: float


def backtest(country: str, test_from: date, test_to: date, train_years: int = 3) -> BacktestResult | None:
    rows = []
    d = test_from
    holidays_cache: set[date] = set()
    while d <= test_to:
        train_from = date(d.year - train_years, d.month, d.day)
        df = load_training(country, train_from, d - timedelta(days=1))
        if len(df) < 90:
            d += timedelta(days=1)
            continue
        # build features on TRAIN, then append the test row separately
        years = range(train_from.year, d.year + 1)
        if not holidays_cache or d.year not in {h.year for h in holidays_cache}:
            holidays_cache = _holidays(country, years)
        feats = _features(df, holidays_cache).dropna()
        if len(feats) < 60:
            d += timedelta(days=1)
            continue
        X = feats[feature_cols()].to_numpy(dtype=float)
        y = feats["demand"].to_numpy(dtype=float)
        model = LinearRegression().fit(X, y)

        # load actual + HDD for the test day
        with conn_ctx() as c:
            r = c.execute(
                """
                SELECT d.nowcast_gwh,
                       (SELECT AVG(hdd_pop) FROM hdd_country_daily WHERE country=? AND date=? AND source='era5')
                FROM demand_country_daily d WHERE d.country=? AND d.date=?
                """,
                (country, d, country, d),
            ).fetchone()
        if not r or r[0] is None:
            d += timedelta(days=1)
            continue
        actual = float(r[0])
        hdd = float(r[1] or 0.0)

        # last 2 demand values for lag features
        prev = df.set_index("date")["demand"]
        lag1 = float(prev.iloc[-1]) if len(prev) else actual
        lag7 = float(prev.iloc[-7]) if len(prev) >= 7 else lag1

        feats_test = {
            "hdd_pop": hdd, "holiday": 1 if d in holidays_cache else 0,
            "lag1": lag1, "lag7": lag7,
        }
        for k in range(1, 7):
            feats_test[f"dow_{k}"] = 1 if d.weekday() == k else 0
        for m in range(2, 13):
            feats_test[f"month_{m}"] = 1 if d.month == m else 0
        xrow = np.array([[feats_test[c] for c in feature_cols()]], dtype=float)
        yhat = float(model.predict(xrow)[0])

        # baselines
        persistence_y = lag1
        clim_window = df.assign(doy=pd.to_datetime(df["date"]).dt.dayofyear)
        clim_y = clim_window[clim_window["doy"] == d.timetuple().tm_yday]["demand"].median()
        clim_y = float(clim_y) if not np.isnan(clim_y) else lag1

        rows.append({"date": d, "actual": actual, "yhat": yhat,
                     "pers": persistence_y, "clim": clim_y})
        d += timedelta(days=1)

    if not rows:
        return None
    out = pd.DataFrame(rows)
    mae = float(np.mean(np.abs(out["actual"] - out["yhat"])))
    rmse = float(np.sqrt(np.mean((out["actual"] - out["yhat"]) ** 2)))
    mape = float(np.mean(np.abs((out["actual"] - out["yhat"]) / np.maximum(out["actual"].abs(), 1.0))))
    pers_mae = float(np.mean(np.abs(out["actual"] - out["pers"])))
    clim_mae = float(np.mean(np.abs(out["actual"] - out["clim"])))
    return BacktestResult(
        country=country, n=len(out),
        mae=mae, rmse=rmse, mape=mape,
        persistence_mae=pers_mae, climatology_mae=clim_mae,
        skill_vs_persistence=(1 - mae / pers_mae) if pers_mae else 0.0,
        skill_vs_climatology=(1 - mae / clim_mae) if clim_mae else 0.0,
    )


def run_all(countries: list[str], months_test: int = 6, train_years: int = 3) -> list[BacktestResult]:
    today = date.today()
    test_from = today - timedelta(days=30 * months_test)
    test_to = today - timedelta(days=1)
    results = []
    for c in countries:
        log.info("backtest %s %s..%s", c, test_from, test_to)
        res = backtest(c, test_from, test_to, train_years=train_years)
        if res is None:
            continue
        results.append(res)
        log.info(
            "%s n=%d MAE=%.0f vs pers=%.0f (skill=%.1f%%) vs clim=%.0f (skill=%.1f%%)",
            c, res.n, res.mae, res.persistence_mae, 100 * res.skill_vs_persistence,
            res.climatology_mae, 100 * res.skill_vs_climatology,
        )
    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--countries", nargs="*", default=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"])
    p.add_argument("--months", type=int, default=6)
    p.add_argument("--train-years", type=int, default=3)
    a = p.parse_args()
    run_all(a.countries, months_test=a.months, train_years=a.train_years)
