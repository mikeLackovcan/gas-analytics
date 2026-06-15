"""Storage endpoints — country aggregates + facility catalog + trajectory."""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/country")
def country_storage(country: str | None = None, days: int = Query(90, ge=1, le=730)):
    end = date.today()
    start = end - timedelta(days=days)
    sql = ("SELECT date, country, full_pct, gas_in_storage_twh, working_gas_volume_twh, "
           "injection_gwh, withdrawal_gwh, net_withdrawal_gwh, consumption_gwh, trend "
           "FROM storage_country_daily WHERE date BETWEEN ? AND ?")
    args: list = [start, end]
    if country:
        sql += " AND country = ?"
        args.append(country.upper())
    sql += " ORDER BY date, country"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [
        {"date": r[0].isoformat(), "country": r[1], "full_pct": r[2],
         "gas_in_storage_twh": r[3], "working_gas_volume_twh": r[4],
         "injection_gwh": r[5], "withdrawal_gwh": r[6],
         "net_withdrawal_gwh": r[7], "consumption_gwh": r[8], "trend": r[9]}
        for r in rows
    ]


@router.get("/facilities")
def list_facilities(country: str | None = None, active_only: bool = True):
    """Storage facility catalog from AGSI /about (no per-facility series on free tier)."""
    sql = ("SELECT id, eic, company_eic, country, operator, name, type, "
           "operational_start_date, operational_end_date "
           "FROM storage_facility WHERE 1=1")
    args: list = []
    if country:
        sql += " AND country = ?"
        args.append(country.upper())
    if active_only:
        sql += " AND (operational_end_date IS NULL OR operational_end_date > CURRENT_DATE)"
    sql += " ORDER BY country, name"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [
        {"id": r[0], "eic": r[1], "company_eic": r[2], "country": r[3],
         "operator": r[4], "name": r[5], "type": r[6],
         "operational_start_date": r[7].isoformat() if r[7] else None,
         "operational_end_date": r[8].isoformat() if r[8] else None}
        for r in rows
    ]


@router.get("/eu-target")
def eu_target(target_date: date | None = None, target_pct: float = 90.0):
    """Trajectory of EU storage fullness vs the 90% by Nov 1 mandate."""
    end = date.today()
    start = date(end.year, 4, 1)
    with conn_ctx() as c:
        rows = c.execute(
            """
            SELECT date, AVG(full_pct) AS eu_avg
            FROM storage_country_daily
            WHERE date BETWEEN ? AND ?
              AND country IN ('DE','NL','FR','IT','AT','CZ','BE','PL','ES','SK','HU')
            GROUP BY date ORDER BY date
            """,
            (start, end),
        ).fetchall()
    deadline = target_date or date(end.year, 11, 1)
    return {
        "target_pct": target_pct,
        "target_date": deadline.isoformat(),
        "series": [{"date": r[0].isoformat(), "eu_avg_pct": r[1]} for r in rows],
    }


@router.get("/trajectory")
def trajectory(country: str = "DE", target_pct: float = 90.0):
    """Year-to-date fullness for `country` with 5y day-of-year band (P10/P50/P90).

    Series:
      - actual_pct: current year's daily series so far
      - p10/p50/p90: percentiles across the prior 5 calendar years for the same DOY
      - required_pct: linear path from today's value to `target_pct` on Nov 1
    """
    country = country.upper()
    today = date.today()
    year_start = date(today.year, 1, 1)
    nov1 = date(today.year, 11, 1)

    with conn_ctx() as c:
        actual = c.execute(
            "SELECT date, full_pct FROM storage_country_daily WHERE country = ? AND date BETWEEN ? AND ? ORDER BY date",
            (country, year_start, today),
        ).fetchall()
        band = c.execute(
            """
            SELECT
              CAST(strftime('%j', date) AS INTEGER) AS doy,
              QUANTILE_CONT(full_pct, 0.10) AS p10,
              QUANTILE_CONT(full_pct, 0.50) AS p50,
              QUANTILE_CONT(full_pct, 0.90) AS p90
            FROM storage_country_daily
            WHERE country = ?
              AND EXTRACT(YEAR FROM date) BETWEEN ? AND ?
            GROUP BY doy
            ORDER BY doy
            """,
            (country, today.year - 5, today.year - 1),
        ).fetchall()

    current_pct = actual[-1][1] if actual else None
    required: list[dict] = []
    if current_pct is not None and today < nov1:
        days_to = (nov1 - today).days
        if days_to > 0 and target_pct > current_pct:
            slope = (target_pct - current_pct) / days_to
            for i in range(days_to + 1):
                d = today + timedelta(days=i)
                required.append({"date": d.isoformat(), "pct": round(current_pct + slope * i, 2)})

    return {
        "country": country,
        "target_pct": target_pct,
        "target_date": nov1.isoformat(),
        "current_pct": current_pct,
        "actual": [{"date": r[0].isoformat(), "pct": r[1]} for r in actual],
        "band_by_doy": [{"doy": r[0], "p10": r[1], "p50": r[2], "p90": r[3]} for r in band],
        "required_path": required,
    }
