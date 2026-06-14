from datetime import date, timedelta
from fastapi import APIRouter, Query
from ..db import conn_ctx

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.get("/")
def prices(
    hub: str | None = None,
    contract: str = "M+1",
    days: int = Query(180, ge=1, le=3650),
):
    end = date.today()
    start = end - timedelta(days=days)
    sql = "SELECT date, hub, contract, settle_eur_mwh, source FROM price_daily WHERE date BETWEEN ? AND ? AND contract = ?"
    args: list = [start, end, contract]
    if hub:
        sql += " AND hub = ?"
        args.append(hub.upper())
    sql += " ORDER BY date, hub"
    with conn_ctx() as c:
        rows = c.execute(sql, args).fetchall()
    return [
        {"date": r[0].isoformat(), "hub": r[1], "contract": r[2], "settle_eur_mwh": r[3], "source": r[4]}
        for r in rows
    ]


@router.get("/latest")
def latest_per_hub():
    with conn_ctx() as c:
        rows = c.execute(
            """
            SELECT hub, contract, MAX(date) AS d
            FROM price_daily
            GROUP BY hub, contract
            """
        ).fetchall()
        out = []
        for hub, contract, d in rows:
            r = c.execute(
                "SELECT settle_eur_mwh, source FROM price_daily WHERE hub = ? AND contract = ? AND date = ?",
                (hub, contract, d),
            ).fetchone()
            out.append({"hub": hub, "contract": contract, "date": d.isoformat(), "settle_eur_mwh": r[0], "source": r[1]})
    return out
