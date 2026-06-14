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

## 7. Recommended next sprint (1–2 wk)

Tackle in order, each is mostly independent:

1. **Add migrations + extend AGSI ingest to per-facility.** ~½ day. Unlocks 1.1 and 4.1.
2. **AGSI consumption → `demand_country_daily` populated directly.** ~2h. Collapses Phase 2 to a baseline.
3. **3y historical backfill of AGSI + ALSI + ENTSOG.** ~1 day. Bulk of model training data.
4. **ECMWF HDD ingest + climatology.** ~1.5 days. Unblocks forecast.
5. **TTF/PEG/THE EEX settle scraper.** ~½ day.
6. **MapLibre + deck.gl arcs on `/map`.** ~1 day. The wow-factor view.
7. **Storage trajectory vs target chart on `/storage`.** ~½ day. Alpha overlay 4.1.
8. **APScheduler with the four jobs.** ~½ day. Makes the dashboard self-updating.

Skip for now (parking lot, raise to sprint 2): Norway gassco, UK NTS, VIP unwinding, cargo arrival scraper, gas-for-power coupling.

---

## 8. What we should NOT build

- Vessel-level cargo tracking (Kpler/Vortexa replacement). Massive scope, low marginal value over ALSI inventory deltas + scheduled arrivals.
- Multi-tenant auth / RBAC. Single user.
- Mobile UI.
- Intraday gas-power optimization. Different product.
- Order book / market depth. Different product.
