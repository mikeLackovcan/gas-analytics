from datetime import date, timedelta
from fastapi import APIRouter, Query, BackgroundTasks
from ..db import conn_ctx

router = APIRouter(prefix="/api/demand", tags=["demand"])


@router.get("/nowcast")
def nowcast(country: str | None = None, days: int = Query(60, ge=1, le=365)):
    end = date.today()
    start = end - timedelta(days=days)
    sql = "SELECT date, country, nowcast_gwh, model_version FROM demand_country_daily WHERE date BETWEEN ? AND ?"
    args: list = [start, end]
    if country:
        sql += " AND country = ?"
        args.append(country.upper())
    sql += " ORDER BY date, country"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [{"date": r[0].isoformat(), "country": r[1], "nowcast_gwh": r[2], "model_version": r[3]} for r in rows]


@router.post("/backtest")
def run_backtest(bg: BackgroundTasks, months: int = 6, train_years: int = 3):
    """Walk-forward backtest. Returns 'scheduled'; results in app logs."""
    from ..forecast.backtest import run_all
    bg.add_task(
        run_all,
        countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
        months_test=months,
        train_years=train_years,
    )
    return {"status": "scheduled", "months": months, "train_years": train_years}


@router.post("/forecast/refresh")
def refresh_forecast(bg: BackgroundTasks, train_years: int = 3, horizon_days: int = 10):
    """Trigger LDZ refit + forecast persist in the background."""
    from ..forecast.ldz import fit_and_forecast_all
    bg.add_task(
        fit_and_forecast_all,
        countries=["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"],
        train_years=train_years,
        horizon_days=horizon_days,
    )
    return {"status": "scheduled", "train_years": train_years, "horizon_days": horizon_days}


@router.get("/forecast")
def forecast(country: str | None = None, horizon_days: int = Query(10, ge=1, le=30)):
    with conn_ctx() as c:
        if country:
            run_ts = c.execute(
                "SELECT MAX(run_ts) FROM demand_forecast WHERE country = ?",
                (country.upper(),),
            ).fetchone()[0]
        else:
            run_ts = c.execute("SELECT MAX(run_ts) FROM demand_forecast").fetchone()[0]
        if not run_ts:
            return {"run_ts": None, "horizon_days": horizon_days, "series": []}
        sql = "SELECT target_date, country, gwh, p10, p90, model_version FROM demand_forecast WHERE run_ts = ?"
        args: list = [run_ts]
        if country:
            sql += " AND country = ?"
            args.append(country.upper())
        sql += " ORDER BY target_date, country"
        rows = c.execute(sql, args).fetchall()
    return {
        "run_ts": run_ts.isoformat() if run_ts else None,
        "horizon_days": horizon_days,
        "series": [
            {"target_date": r[0].isoformat(), "country": r[1], "gwh": r[2], "p10": r[3], "p90": r[4], "model_version": r[5]}
            for r in rows
        ],
    }
