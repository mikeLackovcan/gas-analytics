from fastapi import APIRouter
from ..db import conn_ctx

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/countries")
def countries():
    with conn_ctx() as c:
        rows = c.execute(
            "SELECT code, name, tz, population, has_demand_model FROM country ORDER BY code"
        ).fetchall()
    return [
        {"code": r[0], "name": r[1], "tz": r[2], "population": r[3], "has_demand_model": r[4]}
        for r in rows
    ]


@router.get("/storage-facilities")
def storage_facilities():
    with conn_ctx() as c:
        rows = c.execute(
            "SELECT id, country, operator, name, working_gas_twh, max_inj_gwh_d, max_wdr_gwh_d FROM storage_facility ORDER BY country, name"
        ).fetchall()
    return [
        {"id": r[0], "country": r[1], "operator": r[2], "name": r[3], "working_gas_twh": r[4], "max_inj_gwh_d": r[5], "max_wdr_gwh_d": r[6]}
        for r in rows
    ]
