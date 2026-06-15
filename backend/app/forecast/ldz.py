"""LDZ-style demand forecast per country.

Model v0.2 (OLS):
    demand ~ HDD_pop
           + dow_dummies
           + month_dummies
           + holiday
           + lag1 + lag7
    target: nowcast_gwh from demand_country_daily (mass-balance derived)
    HDD source: era5 for history, open-meteo-fcst for D+1..D+15

Quantile bounds (P10/P90) are derived empirically from training residuals,
not from a quantile regression (sufficient for v0.2; revisit at v0.3).

Skill baselines: persistence (lag1), persistence-week (lag7), climatology
(per-DOY 5y median). MAE/RMSE/MAPE per country logged on every fit.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from ..db import conn_ctx, init_schema

log = logging.getLogger("forecast.ldz")

MODEL_VERSION = "ldz-ols-v0.2"


@dataclass
class FitResult:
    country: str
    n_train: int
    mae: float
    rmse: float
    mape: float
    persistence_mae: float
    climatology_mae: float
    residual_std: float
    coefs: dict[str, float] = field(default_factory=dict)


def _holidays(country: str, years: range) -> set[date]:
    try:
        import holidays
        cls = holidays.country_holidays(country, years=list(years))
        return set(cls.keys())
    except Exception:
        return set()


def _features(df: pd.DataFrame, holidays: set[date]) -> pd.DataFrame:
    out = df.copy()
    out["dow"] = pd.to_datetime(out["date"]).dt.dayofweek
    out["month"] = pd.to_datetime(out["date"]).dt.month
    out["holiday"] = out["date"].apply(lambda d: 1 if d in holidays else 0).astype(int)
    # one-hot dow (skip Monday baseline) and month (skip Jan)
    for d in range(1, 7):
        out[f"dow_{d}"] = (out["dow"] == d).astype(int)
    for m in range(2, 13):
        out[f"month_{m}"] = (out["month"] == m).astype(int)
    out["lag1"] = out["demand"].shift(1)
    out["lag7"] = out["demand"].shift(7)
    return out


def _design(features: pd.DataFrame, cols: list[str]) -> np.ndarray:
    return features[cols].to_numpy(dtype=float)


def feature_cols() -> list[str]:
    cols = ["hdd_pop", "holiday", "lag1", "lag7"]
    cols += [f"dow_{d}" for d in range(1, 7)]
    cols += [f"month_{m}" for m in range(2, 13)]
    return cols


def load_training(country: str, day_from: date, day_to: date) -> pd.DataFrame:
    """Join demand_country_daily + hdd_country_daily (era5) per country."""
    with conn_ctx() as c:
        rows = c.execute(
            """
            SELECT d.date,
                   d.nowcast_gwh AS demand,
                   AVG(h.hdd_pop) FILTER (WHERE h.source = 'era5') AS hdd_pop
            FROM demand_country_daily d
            LEFT JOIN hdd_country_daily h
              ON h.country = d.country AND h.date = d.date
            WHERE d.country = ? AND d.date BETWEEN ? AND ?
              AND d.nowcast_gwh IS NOT NULL
            GROUP BY d.date, d.nowcast_gwh
            ORDER BY d.date
            """,
            (country, day_from, day_to),
        ).fetchall()
    df = pd.DataFrame(rows, columns=["date", "demand", "hdd_pop"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["hdd_pop"] = df["hdd_pop"].fillna(0.0)
    return df


def fit(country: str, day_from: date, day_to: date) -> tuple[LinearRegression, FitResult] | None:
    df = load_training(country, day_from, day_to)
    if len(df) < 90:
        log.warning("ldz fit %s: too few rows (%d), skip", country, len(df))
        return None
    years = range(day_from.year, day_to.year + 1)
    feats = _features(df, _holidays(country, years)).dropna()
    if len(feats) < 60:
        log.warning("ldz fit %s: too few rows after lag features (%d), skip", country, len(feats))
        return None

    X = _design(feats, feature_cols())
    y = feats["demand"].to_numpy(dtype=float)
    model = LinearRegression().fit(X, y)
    yhat = model.predict(X)
    residuals = y - yhat

    # baselines
    persistence_mae = float(mean_absolute_error(feats["demand"], feats["lag1"]))
    clim = (
        df.assign(doy=pd.to_datetime(df["date"]).dt.dayofyear, year=pd.to_datetime(df["date"]).dt.year)
        .groupby("doy")["demand"].median()
    )
    clim_pred = feats["date"].apply(lambda d: clim.get(d.timetuple().tm_yday, np.nan)).to_numpy()
    mask = ~np.isnan(clim_pred)
    climatology_mae = float(mean_absolute_error(feats["demand"].iloc[mask.nonzero()[0]].to_numpy(), clim_pred[mask])) if mask.any() else float("nan")

    coefs = dict(zip(feature_cols(), model.coef_.tolist()))
    coefs["__intercept__"] = float(model.intercept_)
    res = FitResult(
        country=country,
        n_train=len(feats),
        mae=float(mean_absolute_error(y, yhat)),
        rmse=float(mean_squared_error(y, yhat) ** 0.5),
        mape=float(np.mean(np.abs(residuals / np.maximum(np.abs(y), 1.0)))),
        persistence_mae=persistence_mae,
        climatology_mae=climatology_mae,
        residual_std=float(np.std(residuals)),
        coefs=coefs,
    )
    return model, res


def forecast_path(model: LinearRegression, country: str, horizon_days: int = 10) -> pd.DataFrame:
    """Produce D+1..D+horizon forecast for `country` using ECMWF forecast HDDs.

    Lag features are seeded from the most recent nowcast values, then rolled
    forward (forecast becomes its own lag1)."""
    today = date.today()
    target_dates = [today + timedelta(days=i) for i in range(1, horizon_days + 1)]

    with conn_ctx() as c:
        # Use the latest forecast run per (date, country)
        rows = c.execute(
            """
            SELECT date, hdd_pop
            FROM (
                SELECT date, hdd_pop,
                       ROW_NUMBER() OVER (PARTITION BY date ORDER BY fcst_run DESC) AS rn
                FROM hdd_country_daily
                WHERE country = ? AND source = 'open-meteo-fcst'
                  AND date BETWEEN ? AND ?
            ) WHERE rn = 1 ORDER BY date
            """,
            (country, target_dates[0], target_dates[-1]),
        ).fetchall()
        hdd_map = {d: float(h) for d, h in rows}
        recent = c.execute(
            """
            SELECT date, nowcast_gwh FROM demand_country_daily
            WHERE country = ? AND nowcast_gwh IS NOT NULL
            ORDER BY date DESC LIMIT 7
            """,
            (country,),
        ).fetchall()

    if not recent:
        return pd.DataFrame()
    recent_by_date = {r[0]: float(r[1]) for r in recent}
    holidays = _holidays(country, range(today.year, today.year + 2))

    out_rows = []
    lag1 = recent[0][1]
    for d in target_dates:
        lag7 = recent_by_date.get(d - timedelta(days=7), lag1)
        hdd = hdd_map.get(d, 0.0)
        feats = {
            "hdd_pop": hdd,
            "holiday": 1 if d in holidays else 0,
            "lag1": lag1,
            "lag7": lag7,
        }
        for k in range(1, 7):
            feats[f"dow_{k}"] = 1 if d.weekday() == k else 0
        for m in range(2, 13):
            feats[f"month_{m}"] = 1 if d.month == m else 0
        X = np.array([[feats[c] for c in feature_cols()]], dtype=float)
        yhat = float(model.predict(X)[0])
        out_rows.append({"target_date": d, "gwh": yhat, "hdd_pop": hdd})
        lag1 = yhat  # roll forward
        recent_by_date[d] = yhat

    return pd.DataFrame(out_rows)


def persist_forecast(country: str, fc: pd.DataFrame, residual_std: float) -> int:
    if fc.empty:
        return 0
    init_schema()
    run_ts = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
    # P10/P90 from residual std assuming Gaussian (~1.282 sigma)
    z = 1.282
    with conn_ctx() as c:
        for _, r in fc.iterrows():
            c.execute(
                "INSERT OR REPLACE INTO demand_forecast VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_ts, country, r["target_date"], float(r["gwh"]),
                 float(r["gwh"] - z * residual_std),
                 float(r["gwh"] + z * residual_std),
                 MODEL_VERSION),
            )
    log.info("forecast %s: persisted %d rows @ %s (res_std=%.1f)", country, len(fc), run_ts, residual_std)
    return len(fc)


def fit_and_forecast_all(countries: list[str], train_years: int = 3, horizon_days: int = 10) -> dict[str, FitResult]:
    today = date.today()
    day_from = today - timedelta(days=365 * train_years)
    day_to = today - timedelta(days=1)
    results: dict[str, FitResult] = {}
    for c in countries:
        out = fit(c, day_from, day_to)
        if out is None:
            continue
        model, res = out
        results[c] = res
        fc = forecast_path(model, c, horizon_days=horizon_days)
        persist_forecast(c, fc, res.residual_std)
        log.info(
            "%s n=%d MAE=%.0f vs persist=%.0f vs clim=%.0f (skill_p=%.1f%% skill_c=%.1f%%)",
            c, res.n_train, res.mae, res.persistence_mae, res.climatology_mae,
            100 * (1 - res.mae / res.persistence_mae) if res.persistence_mae else 0,
            100 * (1 - res.mae / res.climatology_mae) if res.climatology_mae else 0,
        )
    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--countries", nargs="*", default=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"])
    p.add_argument("--train-years", type=int, default=3)
    p.add_argument("--horizon", type=int, default=10)
    a = p.parse_args()
    fit_and_forecast_all(a.countries, train_years=a.train_years, horizon_days=a.horizon)
