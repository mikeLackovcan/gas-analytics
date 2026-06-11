# gas-analytics

European gas market analytics — cross-border flows, AGSI storage, ALSI LNG, country demand nowcast/forecast.

See [SPEC.md](SPEC.md) for scope, architecture, and phasing.

## Quick start

```powershell
# 1. Copy backend/.env.example -> backend/.env and set GIE keys
# 2. Run both apps
./start_local.ps1
```

- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Seed reference + run ingest manually

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.reference.seed
python -m app.ingest.agsi
python -m app.ingest.alsi
python -m app.ingest.entsog
```

## Status

Phase 1 scaffold. Ingest skeletons + reference data + API surface + frontend shell wired. HDD, ENTSO-E, demand nowcast and forecast trained models land in Phase 2/3.
