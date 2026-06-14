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


_COUNTRY_CENTROID = {
    "DE": (10.45, 51.16), "NL": (5.29, 52.13), "FR": (2.21, 46.23), "IT": (12.57, 41.87),
    "AT": (14.55, 47.52), "CZ": (15.47, 49.82), "BE": (4.47, 50.50), "PL": (19.13, 51.92),
    "ES": (-3.75, 40.46), "SK": (19.70, 48.67), "HU": (19.50, 47.16), "RO": (24.97, 45.94),
    "BG": (25.49, 42.73), "GR": (21.82, 39.07), "HR": (15.20, 45.10), "SI": (14.99, 46.15),
    "DK": (9.50, 56.26), "IE": (-8.24, 53.41), "PT": (-8.22, 39.40), "LV": (24.60, 56.88),
    "LT": (23.88, 55.17), "EE": (25.01, 58.60), "FI": (25.75, 61.92), "UK": (-3.43, 55.38),
    "CH": (8.23, 46.82), "NO": (8.47, 60.47), "RU": (37.62, 55.75), "UA": (31.17, 48.38),
    "MD": (28.37, 47.41), "TR": (35.24, 38.96), "BY": (27.95, 53.71),
}


@router.get("/arcs")
def flow_arcs(day: date | None = None, days: int = Query(1, ge=1, le=14), min_gwh: float = 5.0):
    """IP-level flows shaped for deck.gl ArcLayer.

    Returns one record per IP per direction (net source->target with positive kwh).
    Endpoints: if the IP has lat/lon from ENTSOG catalog, use it for both sides;
    otherwise fall back to country centroids."""
    end = day or date.today()
    start = end - timedelta(days=days - 1)
    with conn_ctx() as c:
        rows = c.execute(
            """
            SELECT
              ip.id, ip.name, ip.country_from, ip.country_to,
              ip.lon, ip.lat,
              SUM(CASE WHEN f.direction='entry' THEN f.kwh ELSE 0 END) AS entry_kwh,
              SUM(CASE WHEN f.direction='exit'  THEN f.kwh ELSE 0 END) AS exit_kwh
            FROM flow_ip_daily f
            JOIN ip ON ip.id = f.ip_id
            WHERE f.date BETWEEN ? AND ?
            GROUP BY ip.id, ip.name, ip.country_from, ip.country_to, ip.lon, ip.lat
            """,
            (start, end),
        ).fetchall()
    out = []
    for ip_id, name, cf, ct, lon, lat, ent_kwh, ex_kwh in rows:
        net_kwh = (ent_kwh or 0) - (ex_kwh or 0)
        gwh = abs(net_kwh) / 1e6
        if gwh < min_gwh:
            continue
        # source -> target direction follows net flow sign vs catalog orientation
        src, tgt = (cf, ct) if net_kwh < 0 else (ct, cf)
        src_lonlat = _COUNTRY_CENTROID.get(src)
        tgt_lonlat = _COUNTRY_CENTROID.get(tgt)
        if not src_lonlat or not tgt_lonlat:
            continue
        out.append({
            "ip_id": ip_id, "name": name,
            "from": src, "to": tgt,
            "from_lonlat": list(src_lonlat),
            "to_lonlat": list(tgt_lonlat),
            "ip_lonlat": [lon, lat] if (lon is not None and lat is not None) else None,
            "gwh": round(gwh, 1),
        })
    out.sort(key=lambda x: -x["gwh"])
    return {"from_date": start.isoformat(), "to_date": end.isoformat(), "arcs": out}


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
