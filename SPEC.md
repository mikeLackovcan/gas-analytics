# gas-analytics — European Gas Market Analytics

**Owner:** mikef
**Started:** 2026-06-11
**Status:** Phase 1 scaffold

## 1. Purpose

A single dashboard for an EU gas trader / power trader exposed to gas-power coupling:

- See **cross-border physical flows** (country↔country, drillable to IP) on a live map.
- Track **storage fullness** per country and per facility (AGSI+).
- Track **LNG terminal** sendout, inventory, slot bookings (ALSI).
- Compute a daily **mass-balance demand nowcast** per country (LDZ + power + industrial − exports + storage Δ + LNG sendout).
- Produce a **D+1..D+10 demand forecast** per country, driven by HDD + residual-load + industrial baseline.
- Surface **regime breaks** (flow reversals, sendout anomalies, storage trajectory vs EU 90% target).

Existing public tools (BNetzA, AGSI standalone, ENTSOG TP) cover slices. Nothing combines flow map + demand nowcast + LNG state + forecast in one place.

## 2. Scope (v1)

**Countries (full coverage):** DE, NL, FR, IT, AT, CZ, BE, PL, ES.
**Countries (flow map only, no demand forecast):** SK, HU, RO, BG, GR, HR, SI, DK, IE, PT, LV, LT, EE, FI, plus UK as external node.
**Time resolution:** Daily (D+1 confirmed). Intraday provisional where ENTSOG exposes it.
**Forecast horizon:** D+1 to D+10. Skill gated by ECMWF HDD skill (~D+10 ceiling).

Out of scope v1: vessel-level cargo tracking (Kpler/Vortexa-class), intraday gas-power optimisation, market depth/orderbook, P&L blotter.

## 3. Data sources

| Layer | Source | Auth | Freq | Notes |
|---|---|---|---|---|
| Cross-border physical flows | ENTSOG Transparency Platform | None (rate-limited) | D+1 confirmed; intraday provisional | IP-level. Dedupe by reporting side. |
| Nominations / renominations | ENTSOG TP | None | Intraday | Forward signal vs confirmed flow. |
| Storage | GIE AGSI+ API | API key (free) | D+1 | Per country + per facility. Watch rebasing. |
| LNG terminals | GIE ALSI API | API key (free) | D+1 | Sendout, inventory, DTMI. Cargoes inferred from inventory jumps. |
| Power / residual load | ENTSO-E Transparency Platform | API token (free) | H | Gas plant generation + load forecasts. |
| Weather (HDD) | ECMWF Open Data (HRES + ENS), DWD ICON for DE | None | 6-12h cycles | Pop-weighted city HDD per country. |
| Prices | ICE / EEX EOD (TTF, THE, PEG, PVB) | Manual / scraper / paid | EOD | For industrial elasticity term + spark stack. |

API keys/tokens live in `backend/.env`, never in repo.

## 4. Architecture

```
┌────────────────────────────────────────────────────────────────┐
│ Frontend  Next.js + MapLibre + deck.gl + ECharts               │
│   /map       country-pair flow map (sankey or arcs)            │
│   /storage   AGSI tiles + trajectory vs EU 90% target          │
│   /lng       ALSI terminals, sendout, inventory                │
│   /demand    nowcast + D+1..D+10 forecast per country          │
└──────────────────────────────┬─────────────────────────────────┘
                               │ REST (FastAPI)
┌──────────────────────────────┴─────────────────────────────────┐
│ Backend  FastAPI                                                │
│   /api/flows         country-pair daily + IP detail            │
│   /api/storage       per-country, per-facility                 │
│   /api/lng           per-terminal sendout, inventory, capacity │
│   /api/demand        nowcast + forecast                        │
│   /api/balance       country mass-balance residual             │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────┴─────────────────────────────────┐
│ Ingest workers   APScheduler (Phase 1) → Prefect later         │
│   entsog_flows      hourly                                     │
│   agsi              daily 09:00 CET                            │
│   alsi              daily 09:00 CET                            │
│   entsoe            hourly                                     │
│   ecmwf_hdd         after 00z / 12z cycles                     │
└──────────────────────────────┬─────────────────────────────────┘
                               │
┌──────────────────────────────┴─────────────────────────────────┐
│ Storage                                                         │
│   data/raw/<source>/<date>.json     immutable raw              │
│   data/parquet/<table>/...          typed series               │
│   gas.db (SQLite/DuckDB)            entities, forecasts        │
└────────────────────────────────────────────────────────────────┘
```

Stack matches `Energy-prices-claude` so deploy patterns (Fly.io backend, Vercel frontend) carry over.

## 5. Data model

### Entities

- `country (code, name, tz, population, has_demand_model)`
- `tso (code, country, name)`
- `ip (id, name, country_from, country_to, tso_from, tso_to, vip_id, reporting_side, active)`
- `vip (id, name, country_from, country_to, member_ips[])`
- `storage_facility (id, country, operator, working_gas_twh, max_inj_gwh_d, max_wdr_gwh_d)`
- `lng_terminal (id, country, name, capacity_gwh_d, storage_gwh, owner)`

### Series

- `flow_ip_daily (date, ip_id, direction, kwh)`
- `flow_country_pair_daily (date, country_from, country_to, kwh)` — derived
- `storage_country_daily (date, country, full_pct, working_gas_twh, injection_gwh, withdrawal_gwh)`
- `storage_facility_daily (...)`
- `lng_terminal_daily (date, terminal_id, sendout_gwh, inventory_gwh, dtmi_gwh)`
- `power_gas_gen_hourly (datetime, country, gas_mwh)`
- `hdd_country_daily (date, country, hdd_pop, source, fcst_run)`
- `demand_country_daily (date, country, nowcast_gwh, model_version)`
- `demand_forecast (run_ts, country, target_date, gwh, p10, p90, model_version)`

### Mass balance (per country, per day)

```
Demand_total ≈ Σ(entries) − Σ(exits)
             + Withdrawal − Injection
             + LNG_sendout
             − Production_domestic
```

Reconciliation residual vs published TSO sendout (BNetzA / Trading Hub Europe for DE) is the data-quality KPI.

## 6. Forecast model

Per country, daily, three additive components:

**LDZ:** `gwh = β₀ + β₁·HDD_pop + β₂·weekday + β₃·holiday + β₄·lag1 + β₅·lag7`. GBM as challenger to OLS. Refit weekly with 3y rolling window.

**Power-for-gas:** residual_load_forecast → merit-order dispatch (reuse `Energy-prices-claude` stack output) → gas MWh × heat rate (NL/DE ~6.5, IT ~6.8). Phase 3.

**Industrial:** month-of-year baseline + TTF-elasticity term `Δind = γ·log(TTF / TTF_ref)`. Post-2022 elasticity is real (DE −20%).

**Total = LDZ + Power + Industrial.** Publish P10/P50/P90 from quantile regression on residuals. Track skill vs persistence + climatology baselines.

## 7. Phasing

- **Phase 1 — Read-only dashboard (2-3 wk).** ENTSOG + AGSI + ALSI ingest, IP master, country-pair flow map, storage tiles, LNG tiles. Already better than any public tool.
- **Phase 2 — Mass-balance nowcast (2 wk).** Per-country daily demand from mass balance. Backtest harness. LDZ HDD forecast for DE/NL/FR/IT/AT/CZ.
- **Phase 3 — Full forecast (2-3 wk).** Power-for-gas component, industrial elasticity, D+10 surface, P10/P50/P90 bands.
- **Phase 4 — Alerts.** Flow reversal, sendout anomaly, storage trajectory vs 90% target, forecast-vs-actual breach.

## 8. Repo layout

```
gas-analytics/
├── SPEC.md                      this file
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entrypoint
│   │   ├── config.py            settings + env
│   │   ├── db.py                SQLAlchemy / DuckDB session
│   │   ├── models/              ORM + pydantic
│   │   ├── routers/             flows, storage, lng, demand, balance
│   │   ├── ingest/              entsog, agsi, alsi, entsoe, ecmwf
│   │   ├── forecast/            ldz, power, industrial, combine
│   │   └── reference/           IP master, country mapping
│   ├── data/                    raw + parquet (gitignored)
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── app/                     Next.js app router
    │   ├── map/                 country-pair flow map
    │   ├── storage/             AGSI tiles
    │   ├── lng/                 ALSI tiles
    │   └── demand/              forecast view
    ├── components/
    ├── lib/                     API client
    └── package.json
```

## 9. Non-goals / parking lot

- Vessel-level LNG cargo tracking (revisit with Kpler/Vortexa contract or AIS-derived feed).
- Intraday gas-power optimiser.
- Order-book / market microstructure.
- Mobile UI.
- Multi-tenant auth (single user v1).

## 10. Open questions to resolve as we go

- ENTSOG IP-side dedupe rule: prefer "operator" or "adjacent"? Default: operator, override per IP in master table.
- VIP modelling: hide underlying physicals once member IPs are flagged?
- DE industrial elasticity reference TTF (`TTF_ref`): 2019 avg or rolling 5y? Default: rolling 5y median.
- Cargo arrival inference: ALSI inventory jump threshold? Default: > 30% of terminal capacity in 24h.
