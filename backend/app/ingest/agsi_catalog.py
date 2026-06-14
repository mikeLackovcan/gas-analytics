"""Bootstrap the storage company + facility catalog from AGSI /about.

AGSI free tier does not expose per-facility *time series* — only country
aggregates. But the /about endpoint gives us the full hierarchy of SSOs
(companies) and their facilities with authoritative EIC codes, types,
operational dates. We persist that as reference data so:
  - the schema is ready for per-facility series when/if AGSI PRO is added
  - we can group flows / news / unavailability events by company/facility
  - the dashboard can show "DE has 26 SSOs operating N facilities" etc.
"""
from __future__ import annotations

import logging
from datetime import date

from ..config import settings
from ..db import conn_ctx, init_schema
from .common import get_json, save_raw

log = logging.getLogger("ingest.agsi_catalog")


# Map AGSI /about top-level country names to ISO-2 codes.
_NAME_TO_ISO = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR",
    "Czech Republic": "CZ", "Czechia": "CZ", "Denmark": "DK", "Finland": "FI",
    "France": "FR", "Germany": "DE", "Greece": "GR", "Hungary": "HU",
    "Ireland": "IE", "Italy": "IT", "Latvia": "LV", "Lithuania": "LT",
    "Luxembourg": "LU", "Netherlands": "NL", "Poland": "PL", "Portugal": "PT",
    "Romania": "RO", "Slovakia": "SK", "Slovenia": "SI", "Spain": "ES",
    "Sweden": "SE", "Switzerland": "CH", "United Kingdom": "UK", "Ukraine": "UA",
}


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _pub_url(company: dict) -> str | None:
    pl = company.get("publication_link") or []
    if pl and isinstance(pl, list) and pl[0].get("url"):
        return pl[0]["url"]
    return None


def fetch_about() -> dict:
    return get_json(f"{settings.agsi_base_url}/about", headers={"x-key": settings.agsi_api_key})


def upsert(payload: dict) -> tuple[int, int]:
    init_schema()
    europe = (payload.get("SSO") or {}).get("Europe") or {}
    n_companies = 0
    n_facilities = 0
    with conn_ctx() as c:
        c.execute("DELETE FROM storage_facility")
        c.execute("DELETE FROM storage_company")
        for country_name, companies in europe.items():
            iso = _NAME_TO_ISO.get(country_name)
            if not iso:
                continue
            for comp in companies or []:
                ceic = comp.get("eic") or f"{iso}-{comp.get('short_name','?')}"
                c.execute(
                    "INSERT OR REPLACE INTO storage_company VALUES (?, ?, ?, ?, ?)",
                    (ceic, comp.get("short_name"), comp.get("name"), iso, _pub_url(comp)),
                )
                n_companies += 1
                for fac in comp.get("facilities") or []:
                    feic = fac.get("eic")
                    if not feic:
                        continue
                    fcountry = (fac.get("country") or {}).get("code") or iso
                    c.execute(
                        "INSERT OR REPLACE INTO storage_facility VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            feic, feic, ceic, fcountry,
                            comp.get("short_name"),
                            fac.get("name"),
                            fac.get("type"),
                            _parse_date(fac.get("operational_start_date")),
                            _parse_date(fac.get("operational_end_date")),
                            None, None, None,
                        ),
                    )
                    n_facilities += 1
    return n_companies, n_facilities


def run() -> tuple[int, int]:
    p = fetch_about()
    save_raw("agsi", "about_catalog", p)
    n_co, n_fac = upsert(p)
    log.info("agsi catalog: %d companies, %d facilities", n_co, n_fac)
    return n_co, n_fac


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
