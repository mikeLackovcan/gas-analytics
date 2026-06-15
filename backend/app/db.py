import duckdb
from contextlib import contextmanager
from pathlib import Path
from .config import settings


_DB_PATH = settings.data_dir / "gas.duckdb"


def get_conn() -> duckdb.DuckDBPyConnection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(_DB_PATH))


@contextmanager
def conn_ctx():
    c = get_conn()
    try:
        yield c
    finally:
        c.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS country (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tz TEXT,
    population INTEGER,
    has_demand_model BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS tso (
    code TEXT PRIMARY KEY,
    country TEXT,
    name TEXT
);

CREATE TABLE IF NOT EXISTS ip (
    id TEXT PRIMARY KEY,
    name TEXT,
    country_from TEXT,
    country_to TEXT,
    tso_from TEXT,
    tso_to TEXT,
    vip_id TEXT,
    reporting_side TEXT,
    lon DOUBLE,
    lat DOUBLE,
    has_data BOOLEAN DEFAULT TRUE,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS storage_company (
    eic TEXT PRIMARY KEY,
    short_name TEXT,
    name TEXT,
    country TEXT,
    publication_url TEXT
);

CREATE TABLE IF NOT EXISTS storage_facility (
    id TEXT PRIMARY KEY,            -- EIC if known, else fabricated
    eic TEXT,
    company_eic TEXT,
    country TEXT,
    operator TEXT,                  -- short_name of company
    name TEXT,
    type TEXT,                      -- DSR / ASF / UGS / VSP / etc
    operational_start_date DATE,
    operational_end_date DATE,
    working_gas_twh DOUBLE,
    max_inj_gwh_d DOUBLE,
    max_wdr_gwh_d DOUBLE
);

CREATE TABLE IF NOT EXISTS lng_terminal (
    id TEXT PRIMARY KEY,
    country TEXT,
    name TEXT,
    capacity_gwh_d DOUBLE,
    storage_gwh DOUBLE,
    owner TEXT
);

CREATE TABLE IF NOT EXISTS flow_ip_daily (
    date DATE,
    ip_id TEXT,
    operator_key TEXT,
    direction TEXT,
    kwh DOUBLE,
    PRIMARY KEY (date, ip_id, operator_key, direction)
);

CREATE TABLE IF NOT EXISTS storage_country_daily (
    date DATE,
    country TEXT,
    full_pct DOUBLE,
    gas_in_storage_twh DOUBLE,
    working_gas_volume_twh DOUBLE,
    injection_gwh DOUBLE,
    withdrawal_gwh DOUBLE,
    net_withdrawal_gwh DOUBLE,
    consumption_gwh DOUBLE,
    trend DOUBLE,
    PRIMARY KEY (date, country)
);

CREATE TABLE IF NOT EXISTS storage_facility_daily (
    date DATE,
    facility_id TEXT,
    full_pct DOUBLE,
    gas_twh DOUBLE,
    injection_gwh DOUBLE,
    withdrawal_gwh DOUBLE,
    PRIMARY KEY (date, facility_id)
);

CREATE TABLE IF NOT EXISTS lng_terminal_daily (
    date DATE,
    terminal_id TEXT,
    sendout_gwh DOUBLE,
    inventory_gwh DOUBLE,
    dtmi_gwh DOUBLE,
    PRIMARY KEY (date, terminal_id)
);

CREATE TABLE IF NOT EXISTS price_daily (
    date DATE,
    hub TEXT,                 -- TTF / THE / PEG / PVB / NBP / HH / EUA / API2
    settle_eur_mwh DOUBLE,
    contract TEXT,            -- e.g. 'M+1', 'BoM', 'Cal26', 'Win26-27'
    source TEXT,              -- 'csv-manual', 'eex', 'ice', etc
    PRIMARY KEY (date, hub, contract)
);

CREATE TABLE IF NOT EXISTS hdd_country_daily (
    date DATE,
    country TEXT,
    hdd_pop DOUBLE,
    source TEXT,
    fcst_run TIMESTAMP,
    PRIMARY KEY (date, country, source, fcst_run)
);

CREATE TABLE IF NOT EXISTS demand_country_daily (
    date DATE,
    country TEXT,
    nowcast_gwh DOUBLE,
    model_version TEXT,
    PRIMARY KEY (date, country)
);

CREATE TABLE IF NOT EXISTS demand_forecast (
    run_ts TIMESTAMP,
    country TEXT,
    target_date DATE,
    gwh DOUBLE,
    p10 DOUBLE,
    p90 DOUBLE,
    model_version TEXT,
    PRIMARY KEY (run_ts, country, target_date)
);
"""


_SCHEMA_INITIALIZED = False


def init_schema() -> None:
    """Idempotent + memoised within a process so we don't churn connections."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with conn_ctx() as c:
        c.execute(SCHEMA_SQL)
    _SCHEMA_INITIALIZED = True
