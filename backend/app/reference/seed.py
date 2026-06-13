"""Seed reference tables.

`seed_all()` loads static reference (countries, storage facilities, LNG terminals).
IP catalog is bootstrapped from ENTSOG live via `bootstrap_ips()` — call separately
since it needs network. Hand-coded `ips.py` retained only as offline fallback.
"""
import logging

from .countries import COUNTRIES
from .ips import IPS as FALLBACK_IPS
from .storage_facilities import STORAGE_FACILITIES
from .lng_terminals import LNG_TERMINALS
from ..db import conn_ctx, init_schema

log = logging.getLogger("seed")


def seed_all() -> None:
    init_schema()
    with conn_ctx() as c:
        c.execute("DELETE FROM country")
        c.executemany(
            "INSERT INTO country VALUES (?, ?, ?, ?, ?)",
            [(x["code"], x["name"], x["tz"], x["population"], x["has_demand_model"]) for x in COUNTRIES],
        )
        c.execute("DELETE FROM storage_facility")
        c.executemany(
            "INSERT INTO storage_facility VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(
                x["id"], x["country"], x["operator"], x["name"],
                x["working_gas_twh"], x["max_inj_gwh_d"], x["max_wdr_gwh_d"]
            ) for x in STORAGE_FACILITIES],
        )
        c.execute("DELETE FROM lng_terminal")
        c.executemany(
            "INSERT INTO lng_terminal VALUES (?, ?, ?, ?, ?, ?)",
            [(
                x["id"], x["country"], x["name"],
                x["capacity_gwh_d"], x["storage_gwh"], x["owner"]
            ) for x in LNG_TERMINALS],
        )


def bootstrap_ips() -> int:
    """Pull live ENTSOG catalog; fall back to hand-coded list on failure."""
    try:
        from ..ingest.entsog_catalog import run as run_cat
        return run_cat()
    except Exception as e:
        log.warning("ENTSOG catalog fetch failed (%s) — falling back to hand-coded IPs", e)
        with conn_ctx() as c:
            c.execute("DELETE FROM ip")
            for x in FALLBACK_IPS:
                c.execute(
                    "INSERT INTO ip VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (x["id"], x["name"], x["country_from"], x["country_to"],
                     x["tso_from"], x["tso_to"], x["vip_id"], x["reporting_side"],
                     None, None, True, True),
                )
        return len(FALLBACK_IPS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_all()
    n = bootstrap_ips()
    print(f"Reference seeded. IPs: {n}")
