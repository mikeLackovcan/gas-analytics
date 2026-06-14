"""Country mass-balance: Demand = entries - exits + withdrawal - injection + LNG sendout."""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/balance", tags=["balance"])


@router.get("/country")
def country_balance(country: str, days: int = Query(30, ge=1, le=365)):
    country = country.upper()
    end = date.today()
    start = end - timedelta(days=days)
    prefix = f"{country}-"
    with conn_ctx() as c:
        flows = c.execute(
            """
            SELECT f.date,
                   SUM(CASE WHEN f.direction='entry' THEN f.kwh ELSE 0 END) / 1e6 AS entries_gwh,
                   SUM(CASE WHEN f.direction='exit'  THEN f.kwh ELSE 0 END) / 1e6 AS exits_gwh
            FROM flow_ip_daily f
            WHERE f.date BETWEEN ? AND ? AND f.operator_key LIKE ?
            GROUP BY f.date ORDER BY f.date
            """,
            (start, end, prefix + "%"),
        ).fetchall()
        storage = c.execute(
            "SELECT date, injection_gwh, withdrawal_gwh FROM storage_country_daily WHERE country = ? AND date BETWEEN ? AND ?",
            (country, start, end),
        ).fetchall()
        lng = c.execute(
            "SELECT date, sendout_gwh FROM lng_terminal_daily WHERE terminal_id = ? AND date BETWEEN ? AND ?",
            (f"{country}-AGG", start, end),
        ).fetchall()

    s_map = {r[0]: (r[1] or 0, r[2] or 0) for r in storage}
    l_map = {r[0]: (r[1] or 0) for r in lng}
    out = []
    for d, ent, exi in flows:
        inj, wdr = s_map.get(d, (0, 0))
        lng_so = l_map.get(d, 0)
        demand = (ent or 0) - (exi or 0) + (wdr or 0) - (inj or 0) + (lng_so or 0)
        out.append({
            "date": d.isoformat(),
            "entries_gwh": ent,
            "exits_gwh": exi,
            "withdrawal_gwh": wdr,
            "injection_gwh": inj,
            "lng_sendout_gwh": lng_so,
            "implied_demand_gwh": demand,
        })
    return {"country": country, "series": out}
