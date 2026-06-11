from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/lng", tags=["lng"])


@router.get("/country")
def country_lng(country: str | None = None, days: int = Query(60, ge=1, le=365)):
    end = date.today()
    start = end - timedelta(days=days)
    sql = "SELECT date, terminal_id, sendout_gwh, inventory_gwh, dtmi_gwh FROM lng_terminal_daily WHERE date BETWEEN ? AND ?"
    args: list = [start, end]
    if country:
        sql += " AND terminal_id LIKE ?"
        args.append(f"{country.upper()}-%")
    sql += " ORDER BY date, terminal_id"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [
        {"date": r[0].isoformat(), "terminal_id": r[1], "sendout_gwh": r[2], "inventory_gwh": r[3], "dtmi_gwh": r[4]}
        for r in rows
    ]


@router.get("/terminals")
def list_terminals():
    with conn_ctx() as c:
        rows = c.execute(
            "SELECT id, country, name, capacity_gwh_d, storage_gwh, owner FROM lng_terminal ORDER BY country, name"
        ).fetchall()
    return [
        {"id": r[0], "country": r[1], "name": r[2], "capacity_gwh_d": r[3], "storage_gwh": r[4], "owner": r[5]}
        for r in rows
    ]
