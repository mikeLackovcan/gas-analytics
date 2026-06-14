# gas-analytics

European gas market analytics — cross-border flows, AGSI storage, ALSI LNG, country demand nowcast/forecast, weather-driven demand model.

See [SPEC.md](SPEC.md) for scope and architecture, [IMPROVEMENTS.md](IMPROVEMENTS.md) for the research note and roadmap.

## Quick start

```powershell
# 1. Copy backend/.env.example -> backend/.env and set GIE keys (AGSI/ALSI) + ENTSO-E token
# 2. Run both apps
./start_local.ps1
```

- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000

Background scheduler starts with the FastAPI process and refreshes:
- AGSI / ALSI / prices CSV → 09:15-09:35 CET (after GIE publishes)
- Nowcast (mass balance) → 09:35 CET
- ENTSOG flows → every 4h
- ENTSO-E gas generation → hourly
- HDD (ERA5 + ECMWF forecast via Open-Meteo) → 02:30 + 14:30 CET

## Seed reference + backfill manually

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.reference.seed                   # countries, LNG terminals, ENTSOG IP catalog, AGSI /about catalog
python -m app.ingest.backfill_all --years 3    # 3y of AGSI + ALSI + ENTSOG + ENTSO-E
python -m app.ingest.hdd --from 2021-01-01 --to 2026-06-01   # 5y HDD history for the 5y storage band
python -m app.ingest.prices_csv                # picks up CSVs dropped in data/prices/manual/
```

## Prices (manual CSV drop)

Every free public TTF/THE/PEG endpoint we tried was either blocked (Yahoo), paywalled (ICE/EEX direct), or fragile to scrape. The robust path: drop EOD CSVs from your terminal workflow into `backend/data/prices/manual/`. Format (header row required):

```csv
date,hub,contract,settle_eur_mwh
2026-06-13,TTF,M+1,35.42
2026-06-13,TTF,Cal27,38.10
2026-06-13,THE,M+1,35.85
```

Processed files move to `_loaded/` so re-runs are idempotent. Sample in [backend/app/ingest/sample_prices_format.csv](backend/app/ingest/sample_prices_format.csv).

## Status

**Phase 1 — operational dashboard**: scaffold + live ingest for AGSI, ALSI, ENTSOG, ENTSO-E, HDD via Open-Meteo. Frontend has overview, flow map (MapLibre + deck.gl arcs), storage with trajectory vs 90% target + 5y band, LNG, demand pages.

**Next (Phase 2 — forecast)**: train per-country LDZ model on HDD + dow + lag + holiday, plus power-for-gas overlay via ENTSO-E gas-gen. See SPEC.md §6 and IMPROVEMENTS.md §3.
