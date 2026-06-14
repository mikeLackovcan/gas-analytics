"""ENTSO-E Transparency Platform ingest.

Docs: https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html
Auth: securityToken=<token> query param.
Response: XML.

For gas-analytics we ingest:
  - A75 (Actual generation per type, gas) hourly per bidding zone
  - A65 (Total load) hourly per bidding zone — for residual load context

Bidding zone EIC codes for the countries with demand model.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.entsoe")

# 10YXX EIC bidding zones (single-zone countries; DE/AT/LU has special handling pre/post 2018 — using DE-LU).
BZ_EIC = {
    "DE": "10Y1001A1001A82H",   # DE-LU
    "NL": "10YNL----------L",
    "FR": "10YFR-RTE------C",
    "IT": "10YIT-GRTN-----B",   # IT North as proxy; full IT requires merging zones
    "AT": "10YAT-APG------L",
    "CZ": "10YCZ-CEPS-----N",
    "BE": "10YBE----------2",
    "PL": "10YPL-AREA-----S",
    "ES": "10YES-REE------0",
}

NS = {"e": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}


def _yyyymmddhhmm(d: datetime) -> str:
    return d.strftime("%Y%m%d%H%M")


def fetch_xml(params: dict) -> str:
    """ENTSO-E returns XML; we use httpx via get_json's underlying client at text level."""
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=30))
    def _do() -> str:
        with httpx.Client(timeout=60.0) as c:
            r = c.get(settings.entsoe_base_url, params=params)
            r.raise_for_status()
            return r.text

    return _do()


def fetch_gas_gen(country: str, day_from: date, day_to: date) -> str | None:
    eic = BZ_EIC.get(country)
    if not eic or not settings.entsoe_api_token:
        return None
    params = {
        "securityToken": settings.entsoe_api_token,
        "documentType": "A75",
        "processType": "A16",
        "psrType": "B04",   # Fossil Gas
        "in_Domain": eic,
        "periodStart": _yyyymmddhhmm(datetime.combine(day_from, datetime.min.time())),
        "periodEnd":   _yyyymmddhhmm(datetime.combine(day_to,   datetime.min.time())),
    }
    try:
        return fetch_xml(params)
    except Exception as e:
        log.warning("entsoe gas-gen %s %s..%s failed: %s", country, day_from, day_to, e)
        return None


def _strip_ns(xml: str) -> ET.Element:
    """Strip default namespace so we can use plain tag names."""
    import re
    cleaned = re.sub(r'\sxmlns="[^"]+"', "", xml, count=1)
    return ET.fromstring(cleaned)


def parse_a75(xml: str) -> list[tuple[datetime, float]]:
    """Yield (utc_dt, mw) points. ENTSO-E A75 uses PT60M periods."""
    root = _strip_ns(xml)
    out: list[tuple[datetime, float]] = []
    for ts in root.iter("TimeSeries"):
        period = ts.find("Period")
        if period is None:
            continue
        start_str = period.findtext("timeInterval/start") or ""
        try:
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        resolution = period.findtext("resolution") or "PT60M"
        step = timedelta(minutes=60 if resolution == "PT60M" else 15)
        for pt in period.iter("Point"):
            pos = int(pt.findtext("position") or "1")
            qty = pt.findtext("quantity")
            if qty is None:
                continue
            try:
                mw = float(qty)
            except ValueError:
                continue
            out.append((start + step * (pos - 1), mw))
    return out


def run(country: str = "DE", days_back: int = 3,
        day_from: date | None = None, day_to: date | None = None) -> int:
    init_schema()
    today = date.today()
    if day_from is None or day_to is None:
        day_from = today - timedelta(days=days_back)
        day_to = today
    xml = fetch_gas_gen(country, day_from, day_to)
    if not xml:
        return 0
    save_raw("entsoe", f"gas_gen_{country}_{day_from}_{day_to}", xml, dt=today)
    points = parse_a75(xml)
    if not points:
        log.info("entsoe %s %s..%s: no points parsed", country, day_from, day_to)
        return 0
    import pandas as pd
    df = pd.DataFrame(points, columns=["datetime", "gas_mw"])
    df["country"] = country
    out_dir = settings.parquet_dir / "power_gas_gen_hourly"
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / f"{country}_{day_from}_{day_to}.parquet"
    df.to_parquet(fp, index=False)
    log.info("entsoe %s: %d points (%s..%s) -> %s", country, len(df), day_from, day_to, fp)
    return len(df)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser()
    p.add_argument("--country")
    p.add_argument("--from", dest="from_")
    p.add_argument("--to", dest="to_")
    p.add_argument("--days", type=int, default=3)
    a = p.parse_args()
    countries = [a.country] if a.country else list(BZ_EIC.keys())
    for c in countries:
        if a.from_ and a.to_:
            run(c, day_from=date.fromisoformat(a.from_), day_to=date.fromisoformat(a.to_))
        else:
            run(c, days_back=a.days)
