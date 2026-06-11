from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/country")
def country_storage(country: str | None = None, days: int = Query(90, ge=1, le=730)):
    end = date.today()
    start = end - timedelta(days=days)
    sql = "SELECT date, country, full_pct, working_gas_twh, injection_gwh, withdrawal_gwh FROM storage_country_daily WHERE date BETWEEN ? AND ?"
    args: list = [start, end]
    if country:
        sql += " AND country = ?"
        args.append(country.upper())
    sql += " ORDER BY date, country"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [
        {"date": r[0].isoformat(), "country": r[1], "full_pct": r[2], "working_gas_twh": r[3], "injection_gwh": r[4], "withdrawal_gwh": r[5]}
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
