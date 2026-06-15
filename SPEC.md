# gas-analytics — European Gas Market Analytics

**Owner:** mikef
**Started:** 2026-06-11
**Status:** Phase 1 complete — operational dashboard live; Phase 2 (forecast fit) in progress
**Last updated:** 2026-06-15

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

## 3. Data sources (live)

| Layer | Source | Auth | Freq | Status | Notes |
|---|---|---|---|---|---|
| Cross-border physical flows | ENTSOG Transparency Platform `/operationalData` | None | D+1 + intraday | live | Per-operator attribution (`operator_key LIKE 'C-%'`) to avoid double counting between adjacent TSOs. |
| IP catalog | ENTSOG `/interconnections` | None | Daily refresh | live | 170 cross-border IPs with lat/lon. |
| Storage country agg | GIE AGSI+ `/?country=…` | API key (free) | D+1 | live | `consumption` is seasonal avg, NOT daily actual — see §6.1. |
| Storage company/facility catalog | GIE AGSI+ `/about` | API key (free) | Daily | live | 66 companies, 121 facilities with EICs/types/dates. |
| Storage per-facility series | GIE AGSI+ PRO | Paid | — | **gap** | Free tier silently falls back to country agg. |
| LNG country agg | GIE ALSI `/?country=…` | API key (free) | D+1 | live | Sendout, inventory.gwh, dtmi.gwh. |
| LNG per-terminal series | GIE ALSI per-terminal | Free | — | **gap** (planned) | Map to our terminal IDs via `url` slug. |
| Power gas generation | ENTSO-E TP A75 + psrType B04 | API token (free) | Hourly | live | Per bidding zone; persisted to parquet `power_gas_gen_hourly/`. |
| HDD (history) | Open-Meteo ERA5 (`/v1/era5`) | None | Daily, D-2 back | live | Pop-weighted city HDDs for 9 model countries. |
| HDD (forecast) | Open-Meteo ECMWF IFS 0.25 (`/v1/forecast`) | None | 2x daily | live | D+1..D+15. |
| Prices TTF/THE/PEG/PVB | Manual CSV drop → `data/prices/manual/` | n/a | EOD | live | Yahoo + EEX direct both blocked/paywalled; user supplies EOD CSV from terminal access. Format documented in README. |

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

### Entities (current schema)

- `country (code, name, tz, population, has_demand_model)`
- `tso (code, country, name)`
- `ip (id, name, country_from, country_to, tso_from, tso_to, vip_id, reporting_side, lon, lat, has_data, active)` — populated from ENTSOG `/interconnections`
- `storage_company (eic, short_name, name, country, publication_url)` — AGSI `/about`
- `storage_facility (id, eic, company_eic, country, operator, name, type, operational_start_date, operational_end_date, working_gas_twh, max_inj_gwh_d, max_wdr_gwh_d)` — AGSI `/about`
- `lng_terminal (id, country, name, capacity_gwh_d, storage_gwh, owner)` — hand-coded reference

### Series

- `flow_ip_daily (date, ip_id, operator_key, direction, kwh)` — **PK includes operator** to avoid double-counting between adjacent TSOs
- `storage_country_daily (date, country, full_pct, gas_in_storage_twh, working_gas_volume_twh, injection_gwh, withdrawal_gwh, net_withdrawal_gwh, consumption_gwh, trend)`
- `storage_facility_daily (date, facility_id, full_pct, gas_twh, injection_gwh, withdrawal_gwh)` — schema only; needs AGSI PRO
- `lng_terminal_daily (date, terminal_id, sendout_gwh, inventory_gwh, dtmi_gwh)` — currently aggregated as `terminal_id='<C>-AGG'` country-rollups
- `hdd_country_daily (date, country, hdd_pop, source, fcst_run)` — source ∈ {era5, open-meteo-fcst}
- `price_daily (date, hub, settle_eur_mwh, contract, source)` — manual CSV drop
- `power_gas_gen_hourly` — parquet only (`data/parquet/power_gas_gen_hourly/<C>_<from>_<to>.parquet`)
- `demand_country_daily (date, country, nowcast_gwh, model_version)` — written by `demand_nowcast` job (model_version='mass-balance-v0.1')
- `demand_forecast (run_ts, country, target_date, gwh, p10, p90, model_version)` — Phase 2 LDZ model

### Mass balance (per country, per day)

```
Demand_total ≈ Σ(entries_C) − Σ(exits_C)
             + Withdrawal − Injection
             + LNG_sendout
             − Production_domestic         # not yet captured: NO, NL Groningen tail, DK, RO, UK
```

Where `entries_C`/`exits_C` are summed across **rows from operators in country C** (operator_key prefix matches), not by IP country_from/_to. This is the critical correction discovered during smoke-test: ENTSOG reports each IP from both adjacent operators with their own direction convention, and aggregating by IP country alone double-counts.

Reconciliation residual vs published TSO sendout (BNetzA / Trading Hub Europe for DE) is the data-quality KPI.

## 6. Forecast model

### 6.1 v0.2 (LDZ OLS, shipped 2026-06-15)

Per-country LDZ baseline:

```
demand ~ HDD_pop + dow_dummies + month_dummies + holiday + lag1 + lag7
```

- **Training target:** `demand_country_daily.nowcast_gwh` (mass-balance) with **per-month bias correction** to AGSI `consumption` anchor (see 6.2). 2y rolling window.
- **HDD:** ERA5 for training, ECMWF IFS forecast for prediction path. Pop-weighted city HDD per country (top 4-8 cities by pop, base 15.5°C).
- **Forecast:** D+1..D+10. Lag1 rolls forward over the predicted path (forecast becomes its own lag1).
- **Bands:** P10/P90 = P50 ± 1.282·residual_std. P50 and P10 floored at 0 (demand is physical).
- **Skill metrics:** logged per fit vs persistence (yesterday's value) and climatology (5y DOY median).

**Walk-forward 3mo backtest (2026-03..05, 1y train window):**

| Country | MAE | vs climatology | vs persistence |
|---|---|---|---|
| DE | 368 | +47.1% | -16.9% |
| NL | 169 | +55.5% | -24.8% |
| FR | 133 | +54.9% | -7.2% |
| IT | 247 | +59.0% | -13.6% |
| AT | 119 | +35.4% | -43.6% |
| BE | 115 | +32.1% | -93.8% |
| CZ | 82 | +64.3% | -115.8% |
| PL | 137 | +27.9% | -108.4% |
| ES | 364 | -20.8% | -11.2% |

**Reading:** model meaningfully beats climatology (the seasonal expectation) for 8 of 9 countries. It loses to persistence because the mass-balance nowcast target is autocorrelated noise — persistence just copies it. For a *trader's* use case the LDZ output is the right signal: it smooths through noise and captures HDD-driven moves. ES suffers most from gaps (LNG sendout history is only 60d, will improve with backfill).

### 6.2 Known limitations of v0.2

- **Nowcast level bias.** Raw mass balance excludes domestic production (NO, NL Groningen tail, DK, RO, UK). Per-month bias correction using AGSI `consumption` field as anchor brings forecasts into physically plausible range.
- **ALSI history shallow.** Only 60d of LNG sendout in DB; full 2y backfill is queued (ALSI throttles to ~100 req/min so it's a slow background catch-up).
- **No power-for-gas split.** Phase 3 will add gas-gen component from ENTSO-E and couple to residual-load forecast.
- **No TTF elasticity yet.** Drop CSVs in `data/prices/manual/` to unlock.
- **No quantile regression.** Phase 3 will replace residual-std bands with empirical CRPS-calibrated quantiles.

### 6.3 Phase 3 plan

**Power-for-gas:** ENTSO-E gas generation forecast → gas MWh × heat rate (NL/DE ~6.5, IT ~6.8) as additive covariate.
**Industrial elasticity:** `Δind = γ·log(TTF / TTF_5y_median)` once prices are loaded.
**Quantile regression** for honest bands.
**Total = LDZ + Power + Industrial** with per-component attribution surfaced in the UI.

## 7. Phasing

- **Phase 1 — Operational dashboard. ✅ DONE (2026-06-11..15).**
  - ENTSOG + AGSI + ALSI + ENTSO-E + Open-Meteo HDD ingest, all working live.
  - IP master (170 cross-border IPs from ENTSOG catalog, with lat/lon).
  - Storage company/facility catalog (66 SSOs, 121 facilities from AGSI /about).
  - Mass-balance nowcast (operator-attributed, in `demand_country_daily`).
  - Flow map (MapLibre + deck.gl arcs), storage trajectory vs 90% target with 5y band, LNG tiles, demand tiles.
  - Background scheduler (APScheduler) refreshing all feeds on cron.
  - Price ingest via manual CSV drop (free TTF/THE feeds blocked/paywalled).
- **Phase 2 — LDZ forecast. IN PROGRESS.**
  - 5y backfill of AGSI, mass-balance demand, HDD.
  - Per-country LDZ regression: `demand ~ HDD + dow + holiday + lag1 + lag7`. OLS first, GBM challenger.
  - Backtest harness vs persistence + climatology baselines.
  - `/api/demand/forecast` populated daily by scheduled job.
- **Phase 3 — Full forecast.** Power-for-gas via ENTSO-E gas-gen forecast (and Energy-prices-claude residual load), industrial elasticity from TTF, P10/P50/P90 bands.
- **Phase 4 — Alerts.** Flow reversal, sendout anomaly, storage trajectory breach, forecast-vs-actual deviation.

## 8. Repo layout (current)

```
gas-analytics/
├── SPEC.md                      this file
├── README.md                    quick start + CSV format
├── IMPROVEMENTS.md              research note + roadmap
├── start_local.ps1              boots backend + frontend
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entrypoint + lifespan
│   │   ├── config.py            settings (.env via pydantic-settings)
│   │   ├── db.py                DuckDB connection + schema DDL
│   │   ├── scheduler.py         APScheduler jobs (agsi/alsi/entsog/entsoe/hdd/nowcast/prices)
│   │   ├── routers/             flows, storage, lng, demand, balance, prices, meta
│   │   ├── ingest/              agsi, alsi, entsog, entsog_catalog, agsi_catalog,
│   │   │                        entsoe, hdd, prices_csv, demand_nowcast, backfill_all
│   │   ├── forecast/            ldz.py (Phase 2)
│   │   └── reference/           countries, cities (HDD), ips (fallback), lng_terminals,
│   │                            storage_facilities (fallback), seed
│   ├── data/                    raw + parquet + manual CSVs (gitignored)
│   └── requirements.txt
└── frontend/
    ├── src/app/                 Next.js 15 app router
    │   ├── page.tsx             overview tiles
    │   ├── map/                 MapLibre + deck.gl flow arcs
    │   ├── storage/             trajectory vs 90% + 5y band + AGSI table
    │   ├── lng/                 ALSI tiles
    │   └── demand/              nowcast + forecast view
    └── src/lib/api.ts           typed API client
```

## 9. Non-goals / parking lot

- Vessel-level LNG cargo tracking (revisit with Kpler/Vortexa contract or AIS-derived feed).
- Intraday gas-power optimiser.
- Order-book / market microstructure.
- Mobile UI.
- Multi-tenant auth (single user v1).

## 10. Decisions made / open questions

**Resolved:**
- ENTSOG IP-side dedupe: solved via per-operator attribution on flow_ip_daily PK + `operator_key LIKE 'C-%'` filter. No "reporting side" choice needed.
- AGSI consumption: **not** daily actual, it's a seasonal average. Mass balance is the source of truth.
- AGSI per-facility series: PRO-tier only. Catalog (companies + facilities) usable from free `/about`.
- Free TTF/THE/PEG price source: none robust. Manual CSV drop is the path.
- HDD provider: Open-Meteo (ERA5 + ECMWF IFS) — free, no auth, no quota issues at our volumes.

**Open:**
- Norway upstream production (gassco.no) — biggest swing supply, currently absorbed into mass-balance residual.
- UK NTS scrape — UK is not in ENTSOG; need separate ingest for IUK/BBL flow signal.
- VIP unwinding: catalog includes both VIPs and member physicals; flow attribution today still trusts both. If we see persistent over-counting in NW Europe, switch to "VIP wins, hide members".
- Industrial TTF elasticity reference: rolling 5y median vs fixed 2019 baseline — defer until prices are loaded.
- Cargo arrival inference from ALSI inventory deltas: threshold needs tuning per terminal.
- VIP modelling: hide underlying physicals once member IPs are flagged?
- DE industrial elasticity reference TTF (`TTF_ref`): 2019 avg or rolling 5y? Default: rolling 5y median.
- Cargo arrival inference: ALSI inventory jump threshold? Default: > 30% of terminal capacity in 24h.
