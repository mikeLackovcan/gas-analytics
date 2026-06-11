"""Seed reference tables from python lists into DuckDB."""
from .countries import COUNTRIES
from .ips import IPS
from .storage_facilities import STORAGE_FACILITIES
from .lng_terminals import LNG_TERMINALS
from ..db import conn_ctx, init_schema


def seed_all() -> None:
    init_schema()
    with conn_ctx() as c:
        c.execute("DELETE FROM country")
        c.executemany(
            "INSERT INTO country VALUES (?, ?, ?, ?, ?)",
            [(x["code"], x["name"], x["tz"], x["population"], x["has_demand_model"]) for x in COUNTRIES],
        )
        c.execute("DELETE FROM ip")
        c.executemany(
            "INSERT INTO ip VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(
                x["id"], x["name"], x["country_from"], x["country_to"],
                x["tso_from"], x["tso_to"], x["vip_id"], x["reporting_side"], True
            ) for x in IPS],
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


if __name__ == "__main__":
    seed_all()
    print("Reference data seeded.")
