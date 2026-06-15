# Improvements — research note

Status: post-smoke-test on 2026-06-14. Real data confirmed flowing from AGSI, ALSI, ENTSOG, ENTSO-E. This is a forward-looking review of what's missing, what we got wrong, and where to invest next, ranked by trader-value.

---

## 0. Headline finding from the smoke test — CORRECTED 2026-06-14

Initial probe of AGSI showed a `consumption` field per country, and I assumed it was the actual daily demand. **It is not.** A back-to-back probe confirms it is a **seasonal average / "days-of-cover" reference value** — the same number repeats across consecutive days, e.g. DE 2026-06-08..12 all read `consumption=903.9 GWh/d` even though storage `full %` changes daily.

```
2026-06-08  full=35.00   consumption=903.9
2026-06-09  full=35.28   consumption=903.9
2026-06-10  full=35.48   consumption=903.9
2026-06-11  full=35.63   consumption=903.9
2026-06-12  full=35.87   consumption=903.9   ← same value 5 days running
```

**Implication:** SPEC.md §6 is back in force — daily demand nowcast still requires mass-balance reconstruction (entries − exits + withdrawal − injection + LNG_sendout − domestic_production). Per-country actuals from TSOs (BNetzA, THE, GRTgaz, Snam) become the reconciliation target rather than AGSI.

Action: keep storing `consumption_gwh` in `storage_country_daily` as the seasonal reference (useful for "days of cover" tiles), but **do not** populate `demand_country_daily` from it. Mass-balance is the path.

---

## 1. Data gaps to close (ranked by trader-value)

### 1.1 AGSI per-facility (HIGH)
We currently ingest country aggregates only. AGSI exposes `/?type=eu&country=DE&company=...` and per-facility endpoints. Unlocks:
- **Strategic vs commercial split** for DE (Rehden is now state-controlled gas reserve; treating it as freely-available drawdown over-states flexibility).
- **Facility-level injection/withdrawal pacing** — operators time fills around price.
- **Cushion-gas constraints** — pressure-limited withdraw curves at low fill, which the country avg hides.

### 1.2 ALSI per-terminal (HIGH)
Same story. Per-terminal sendout lets you see:
- **DE FSRU utilization**: Wilhelmshaven I vs II vs Brunsbüttel vs Mukran vs Stade — which is leading, which is lagging.
- **Cargo pacing** (inventory deltas → cargo arrivals → forward sendout).
- **Spread between regas capacity and actual sendout** = "import slack" before scarcity forces price up.

### 1.3 ECMWF / DWD HDD ingest (HIGH — blocker for forecast)
Zero weather data today. Day-ahead and 10-day demand forecasts cannot work without this. Concrete plan:
- ECMWF Open Data HRES + ENS (0z / 12z), 2m temperature.
- DWD ICON-EU for DE/AT/CH at higher resolution.
- Population-weighted city HDDs per country (top 5–10 cities by pop, base 15.5°C).
- Persist **climatology** (30y daily normal) alongside live HDD so we can show "HDD anomaly", which is what actually moves demand vs. expectations.

### 1.4 Historical backfill (HIGH — blocker for fits)
Current ingest grabs last 7d. Need 3y minimum for LDZ regression to be meaningful. AGSI permits historical pulls; ENTSOG and ENTSO-E too. Add `--from` / `--to` CLI to each ingest module and a one-shot `backfill_all.py`.

### 1.5 TTF / THE / PEG settlement prices (HIGH)
For:
- Industrial elasticity term (TTF spike → DE industrial demand drop, confirmed empirically since 2022).
- Forward curve context (backwardation/contango shapes storage trajectory expectations).
- Clean spark spread when joined with power prices from Energy-prices-claude.

Source: EEX publishes daily TTF/THE/PEG settles for free via reports portal. Front-month + winter strip is enough for v1.

### 1.6 Norway production (gassco.no) (HIGH)
Norway is the largest **flexible** EU supply. Gassco publishes daily field-by-field production. A single sub-50 MCM/d drop at Troll moves TTF visibly. Currently invisible to our tool because we only see the Norwegian export IPs at Emden/Dornum/Zeebrugge/Dunkerque/Easington — and those reveal it with one-day lag at best.

### 1.7 UK NTS data (HIGH)
UK left ENTSOG. National Grid publishes UK demand, supply, IUK / BBL pipe flows, storage at gov.uk and `mip.nationalgrid.com`. Critical because:
- UK is the largest LNG re-export hub into continental Europe.
- Bacton flows (IUK + BBL) flip direction when continental TTF > NBP and vice versa — leading indicator.

### 1.8 ENTSOG nominations + capacity (MEDIUM)
Today we ingest "Physical Flow" only. Adding:
- **Renominations** = forward-looking intraday signal at IP level.
- **Firm + interruptible capacity** = denominator for utilization. Capacity reductions = maintenance / outages, often pre-flagged.

### 1.9 LNG cargo schedule (MEDIUM)
ALSI exposes upcoming arrivals at most terminals (5–14d horizon) via the `dtrs` / scheduled-vessels endpoints. Free. Skip paid AIS for now.

### 1.10 ENTSOG maintenance calendar (MEDIUM)
Available-capacity reductions are a leading signal of flow disruption — Norway maintenance season in May–Sept is the canonical case.

### 1.11 Türkstream + Trans-Balkan flows (MEDIUM)
Post-2025 Ukraine transit shutdown, Türkstream → BG/RO/HU/SK is the residual Russian pipeline supply. Already covered by ENTSOG IPs (`Negru Vodă/Kardam`, `Sidirokastro/Kulata`) — just needs a dashboard tile.

### 1.12 Industrial demand proxies (LOWER, but distinctive)
Eurostat publishes monthly industrial production indices ~45-day lag. Useful for trend, useless for nowcast. Worth ingesting only after the rest is solid.

---

## 2. Architecture refinements

### 2.1 Schema migrations
`init_schema()` is `CREATE IF NOT EXISTS` only. New columns won't apply to existing DBs (we hit this today and had to drop). Add a version table + idempotent ALTER blocks, or pin to a tiny migration helper (DuckDB has `ALTER TABLE ADD COLUMN`).

### 2.2 Unit normalization
AGSI mixes GWh, MCM, TWh; ENTSOG uses kWh/d; ENTSO-E uses MW. We currently store raw. Normalize at ingest to **GWh** (energy) and **GWh/d** (rates), record conversion in a lookup, keep raw in parquet for audit.

### 2.3 Gas-day vs calendar-day
Gas day = 06:00 UTC to next 06:00 UTC. ENTSOG and AGSI use gas day; our `date` column is ambiguous. Add a `day_type` column or convention doc; misalignment will bite us when joining ENTSO-E (calendar UTC) hourly data to gas-day flows.

### 2.4 Idempotent ingest with audit
`INSERT OR REPLACE` works but kills the audit trail. Move to MERGE with `updated_at` + `source_run_id` columns so we can answer "when did this value change and which run wrote it".

### 2.5 Scheduler
Nothing runs ingest today. Minimum-viable: APScheduler in the FastAPI process with three jobs:
- AGSI / ALSI: 09:00 CET (after GIE publishes D-1)
- ENTSOG: every 4h (provisional intraday + D+1 confirmed)
- ENTSO-E: every 1h
- HDD: after 00z and 12z ECMWF cycles
Graduate to Prefect once we have 5+ jobs and want a UI.

### 2.6 VIP deduplication
Catalog includes VIPs (`VIP-THE-PEG`, `VIP-TTF-THE`, etc.) AND their member physical IPs. Flow data may report on both. Risk of double counting in country-pair aggregation. Build VIP→member-IP map, then at aggregation time pick one or the other (default: VIP, hide members) — and surface that choice in the response so it's auditable.

### 2.7 Rate-limit + politeness
GIE docs recommend ≤ 10 req/s. Tenacity retries on 429 today but no proactive throttle. Add a token bucket.

### 2.8 Tests
Zero today. Worth at minimum:
- Golden-payload parser tests for each ingest (so an API field rename breaks CI, not prod).
- Schema migration tests.
- Forecast backtest snapshot (track MAE per country, alert on > 15% regression).

---

## 3. Forecast model — concrete recipe

Given we now have AGSI consumption directly, the forecast simplifies to:

**Total demand model (per country, daily):**
```
demand_d ~ HDD_pop + dow + holiday + month + lag(d-1) + lag(d-7)
         + power_gen_gas_gwh (residual-load proxy)
         + log(TTF / TTF_ref) (industrial elasticity)
```

Fit with LightGBM (challenger) vs OLS (champion at first for explainability). 3y rolling window, refit weekly. Quantile regression for P10/P90 bands.

**Per-component attribution** (for explanatory tiles, not forecast):
- LDZ component ≈ β·HDD + dow + holiday + month
- Power component ≈ from ENTSO-E gas-gen × heat rate
- Industrial component ≈ residual after LDZ + power, smoothed monthly

**Skill baselines to beat:** persistence (yesterday's value), climatology (30y same-day-of-year mean), HDD-only OLS. Publish a calibration plot per country.

**Forecast horizon ceiling:** ~D+10, set by ECMWF HDD skill. Beyond that, decay to climatology.

---

## 4. Three "alpha" overlays public tools don't combine

These are the differentiators — anyone can show storage charts. These tie multiple feeds into one decision-useful view:

### 4.1 Storage trajectory vs target, broken out
Plot each country's storage % through the year, overlay:
- EU 90% by Nov 1 target line
- 5y range (P10–P90 band) and 5y median
- Required injection rate per day to hit target, vs actual
**Color cells red where actual < required AND fwd-injection-capacity tight.** This is the single most actionable storage view.

### 4.2 Gas-for-power forecast joined to your existing residual-load model
Energy-prices-claude already forecasts DE residual load. Pipe its output into a per-country gas-burn forecast via:
```
gas_mwh = max(0, residual_load - nuclear - lignite_must_run - hard_coal_clean_to_gas_breakeven)
       / heat_rate
```
This converts a power-market signal into a gas-demand signal — the loop power traders intuit but no public dashboard surfaces.

### 4.3 LNG regas slack
For each terminal cluster (DE, NL, BE, FR, IT, ES, UK):
- sendout / sendout_capacity = utilization
- inventory_days_to_empty = inventory / sendout
- next-arrival ETA from cargo schedule
**Spread between current sendout and max capacity = the import slack before prices have to rise to clear.** Track across the EU as one number.

---

## 5. UI/UX upgrades

5.1 **Real map (deck.gl ArcLayer):** we have lat/lon on every IP now. Country polygons from Natural Earth shaded by storage %, arc thickness ∝ flow GWh, animated.

5.2 **Sankey:** country-pair flow as a Sankey on its own tab. Shows the EU as one network. Single most informative gas chart in existence; nobody publishes a daily-updating one.

5.3 **YoY deltas on every tile.** Traders read deltas, not levels.

5.4 **Drilldown chain:** country → facility → IP. Click-through preserves filters.

5.5 **Storage 5y range band** on every country chart. P10–P90 envelope is the trader's reference; absolute levels are noise.

---

## 6. Deploy / infra

6.1 **Backend on Fly.io** (mirrors Energy-prices-claude). DuckDB file lives in a persistent volume.

6.2 **Frontend on Vercel.**

6.3 **Scheduled ingest** runs in the same Fly machine (APScheduler), logs to stdout, alerts via a simple Slack/email webhook on consecutive failures.

6.4 **Backups** = nightly DuckDB → S3.

---

## 7. Sprint completion log

**Sprint 1 (2026-06-11..15) — all 8 items shipped:**

1. ✅ **AGSI per-facility ingest** — pivoted to /about catalog (free tier blocks per-facility series). 121 facilities loaded with EICs, types, dates.
2. ✅ **Demand from AGSI consumption** — discovered AGSI `consumption` is seasonal avg, not actual. Replaced with operator-attributed mass-balance nowcast.
3. ✅ **Historical backfill** — `--from/--to` on every ingest, `backfill_all.py` orchestrator. AGSI async refactor (12x speedup) makes 2y backfill ~20min.
4. ✅ **HDD ingest** — Open-Meteo ERA5 + ECMWF IFS, pop-weighted city HDDs.
5. ✅ **Prices** — Yahoo/EEX both blocked; switched to manual CSV drop with idempotent `_loaded/` archive.
6. ✅ **MapLibre + deck.gl arcs** — `/api/flows/arcs` + dark MapLibre style + arc width by net GWh.
7. ✅ **Storage trajectory vs target** — `/api/storage/trajectory` with 5y DOY P10/P50/P90 band + required-path-to-90% line.
8. ✅ **APScheduler** — 7 cron jobs wired (agsi/alsi/prices/nowcast/forecast/entsog/entsoe/hdd).

**Sprint 2 (in progress) — Phase 2 forecast:**

- ✅ LDZ OLS model (`app/forecast/ldz.py`): demand ~ HDD + dow + month + holiday + lag1 + lag7. P10/P90 from residual std.
- ✅ Walk-forward backtest (`app/forecast/backtest.py`): MAE/RMSE/MAPE + skill vs persistence + skill vs climatology.
- ✅ `/api/demand/forecast/refresh` + `/api/demand/backtest` background-task endpoints.
- ✅ ALSI `/about` catalog (24 EU LNG terminals from LSO hierarchy).
- ✅ `/api/lng/slack` — sendout / utilization / inventory_days_to_empty per country.
- ✅ `/facilities` frontend page — 121 storage facilities by country/operator/type.
- 🔄 2y backfill running for AGSI/ALSI/ENTSOG/HDD; LDZ fit + verification queued.

## 8. Next sprint candidates (sprint 3)

---

Skip for now (raise to sprint 4 unless asked): Norway gassco, UK NTS, VIP unwinding, cargo arrival scraper. Top picks ordered by trader-value:

1. **Gas-for-power coupling** — feed ENTSO-E gas-gen forecast (or your Energy-prices-claude residual-load output) into the LDZ model as a `power_gwh` covariate. Splits demand into LDZ + power components, makes the forecast spark-aware.
2. **TTF curve loaded into industrial elasticity term** — once you drop CSVs, fit `Δind ≈ γ·log(TTF / TTF_5y_median)` and add as covariate. DE industrial demand is real-elastic post-2022.
3. **AGSI consumption as days-of-cover tile** — even though it's a seasonal avg, it's still useful for "days of demand at current draw" overview cards.
4. **Per-IP daily flow detail page** — drill from `/map` arc click into a per-IP time series chart with capacity utilization overlay.
5. **Norway gassco daily production** — biggest swing supply, public daily field-by-field. Reduces mass-balance residual materially for DE/NL/UK/BE/FR (currently the missing `−Production_domestic` term).
6. **Storage 5y P10-P90 band on storage country view** — extends what's on /storage today to per-country small-multiples.
7. **Forecast skill leaderboard endpoint** — `/api/forecast/skill` returning latest backtest MAE/skill per country, surface as a tile on /demand.
8. **Norway flow direction flip alert** — if Norwegian export flow drops below the seasonal P25, fire a Slack/email webhook.

## 9. What we should NOT build

- Vessel-level cargo tracking (Kpler/Vortexa replacement). Massive scope, low marginal value over ALSI inventory deltas + scheduled arrivals.
- Multi-tenant auth / RBAC. Single user.
- Mobile UI.
- Intraday gas-power optimization. Different product.
- Order book / market depth. Different product.
