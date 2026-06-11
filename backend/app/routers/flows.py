from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("/country-pairs")
def country_pair_flows(
    day: date | None = None,
    days: int = Query(1, ge=1, le=30),
):
    """Aggregate country->country net flow (kWh) over the window ending `day`."""
    end = day or date.today()
    start = end - timedelta(days=days - 1)
    with conn_ctx() as c:
        rows = c.execute(
            """
            SELECT
                ip.country_from AS from_,
                ip.country_to   AS to_,
                SUM(CASE WHEN LOWER(f.direction) = 'exit' THEN -f.kwh ELSE f.kwh END) AS net_kwh
            FROM flow_ip_daily f
            JOIN ip ON ip.id = f.ip_id
            WHERE f.date BETWEEN ? AND ?
            GROUP BY ip.country_from, ip.country_to
            ORDER BY net_kwh DESC
            """,
            (start, end),
        ).fetchall()
    return [
        {"from": r[0], "to": r[1], "net_kwh": r[2], "from_date": start.isoformat(), "to_date": end.isoformat()}
        for r in rows
    ]


@router.get("/ip-detail")
def ip_detail(ip_id: str, days: int = Query(30, ge=1, le=365)):
    end = date.today()
    start = end - timedelta(days=days)
    with conn_ctx() as c:
        rows = c.execute(
            "SELECT date, direction, kwh FROM flow_ip_daily WHERE ip_id = ? AND date BETWEEN ? AND ? ORDER BY date",
            (ip_id, start, end),
        ).fetchall()
    return [{"date": r[0].isoformat(), "direction": r[1], "kwh": r[2]} for r in rows]


@router.get("/ips")
def list_ips(active: bool = True):
    with conn_ctx() as c:
        rows = c.execute(
            "SELECT id, name, country_from, country_to, tso_from, tso_to, vip_id FROM ip WHERE active = ?",
            (active,),
        ).fetchall()
    return [
        {"id": r[0], "name": r[1], "country_from": r[2], "country_to": r[3], "tso_from": r[4], "tso_to": r[5], "vip_id": r[6]}
        for r in rows
    ]
