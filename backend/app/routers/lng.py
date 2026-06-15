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


@router.get("/slack")
def lng_slack(days: int = Query(7, ge=1, le=30)):
    """Alpha overlay: per-country LNG import slack.

    slack = sum(capacity_gwh_d for active terminals) - sendout_gwh
    utilization = sendout_gwh / sum(capacity_gwh_d)
    inventory_days_to_empty = inventory / sendout

    Returns latest day per country. NOTE: capacity_gwh_d is NULL on terminals
    loaded from ALSI /about (the endpoint doesn't expose capacities) — values
    only available where the hand-coded fallback is in use OR after a manual
    capacity backfill. We compute and surface what we can.
    """
    with conn_ctx() as c:
        rows = c.execute(
            """
            WITH country_caps AS (
                SELECT country, SUM(capacity_gwh_d) AS cap_total_gwh_d
                FROM lng_terminal
                WHERE capacity_gwh_d IS NOT NULL
                GROUP BY country
            ),
            latest AS (
                SELECT terminal_id, MAX(date) AS d
                FROM lng_terminal_daily
                GROUP BY terminal_id
            )
            SELECT
                SUBSTRING(l.terminal_id, 1, 2) AS country,
                l.date,
                l.sendout_gwh,
                l.inventory_gwh,
                cc.cap_total_gwh_d
            FROM lng_terminal_daily l
            JOIN latest lt ON lt.terminal_id = l.terminal_id AND lt.d = l.date
            LEFT JOIN country_caps cc ON cc.country = SUBSTRING(l.terminal_id, 1, 2)
            ORDER BY country
            """
        ).fetchall()
    out = []
    for country, d, send, inv, cap in rows:
        send_v = float(send or 0)
        utilization = (send_v / cap) if cap else None
        days_to_empty = (float(inv or 0) / send_v) if send_v > 0 else None
        out.append({
            "country": country,
            "date": d.isoformat(),
            "sendout_gwh": send_v,
            "inventory_gwh": float(inv or 0),
            "capacity_gwh_d": cap,
            "slack_gwh_d": (cap - send_v) if cap else None,
            "utilization": round(utilization, 3) if utilization is not None else None,
            "inventory_days_to_empty": round(days_to_empty, 1) if days_to_empty is not None else None,
        })
    return out
