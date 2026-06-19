import { api, StorageRow, LngRow } from "@/lib/api";

type CountryPairFlow = { from: string; to: string; net_kwh: number };
type Forecast = { country: string; gwh: number; target_date: string };
type ForecastResp = { run_ts: string | null; series: Forecast[] };

async function getOverview() {
  const [storage, lng, flows, fcDE] = await Promise.all([
    api<StorageRow[]>("/api/storage/country?days=1").catch(() => [] as StorageRow[]),
    api<LngRow[]>("/api/lng/country?days=1").catch(() => [] as LngRow[]),
    api<{ arcs: CountryPairFlow[] }>("/api/flows/arcs?days=1&min_gwh=10").catch(() => ({ arcs: [] as CountryPairFlow[] })),
    api<ForecastResp>("/api/demand/forecast?country=DE&horizon_days=5").catch(() => ({ run_ts: null, series: [] as Forecast[] })),
  ]);
  return { storage, lng, flows: flows.arcs, fcDE };
}

function colorFor(pct: number | null) {
  if (pct === null) return "var(--fg-mute)";
  if (pct >= 90) return "var(--green)";
  if (pct >= 70) return "var(--amber)";
  if (pct >= 50) return "var(--fg)";
  return "var(--red)";
}

export default async function Home() {
  const { storage, lng, flows, fcDE } = await getOverview();
  const sorted = [...storage].sort((a, b) => (b.full_pct ?? 0) - (a.full_pct ?? 0));
  const euAvg = storage.length ? storage.reduce((s, r) => s + (r.full_pct ?? 0), 0) / storage.length : null;
  const lngTotal = lng.reduce((s, r) => s + (r.sendout_gwh ?? 0), 0);
  const lngActive = lng.filter((r) => (r.sendout_gwh ?? 0) > 5).length;
  const inj = storage.reduce((s, r) => s + (r.injection_gwh ?? 0), 0);
  const wdr = storage.reduce((s, r) => s + (r.withdrawal_gwh ?? 0), 0);
  const net = inj - wdr;
  const topArc = flows[0];
  const fcMaxDE = fcDE.series.length ? Math.max(...fcDE.series.map((p) => p.gwh)) : null;

  return (
    <div className="grid" style={{ gap: 8 }}>
      {/* KPI strip */}
      <div className="grid c-6">
        <div className="panel kpi">
          <div className="panel-h"><span>EU STORAGE</span><span className="badge">D-1</span></div>
          <div className="big amber">{euAvg === null ? "—" : `${euAvg.toFixed(1)}%`}</div>
          <div className="sub">Avg across {storage.length} countries · target 90% Nov 1</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>NET INJ - WDR</span><span className="badge">GWh/d</span></div>
          <div className="big" style={{ color: net >= 0 ? "var(--green)" : "var(--red)" }}>
            {net >= 0 ? "+" : ""}{net.toFixed(0)}
          </div>
          <div className="sub">Inj {inj.toFixed(0)} · Wdr {wdr.toFixed(0)}</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>LNG SENDOUT</span><span className="badge">GWh/d</span></div>
          <div className="big">{lngTotal.toFixed(0)}</div>
          <div className="sub">{lngActive} terminals active</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>TOP X-BORDER</span><span className="badge">GWh/d</span></div>
          <div className="big amber">{topArc ? `${(Math.abs(topArc.net_kwh) / 1e6).toFixed(0)}` : "—"}</div>
          <div className="sub">{topArc ? `${topArc.from} → ${topArc.to}` : "no flow data"}</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>DE FCST PEAK</span><span className="badge">D+1..D+5</span></div>
          <div className="big">{fcMaxDE === null ? "—" : fcMaxDE.toFixed(0)}</div>
          <div className="sub">GWh/d · LDZ OLS v0.2</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>STATUS</span><span className="badge">PHASE 2</span></div>
          <div className="big" style={{ color: "var(--green)" }}>● LIVE</div>
          <div className="sub">7 ingest jobs scheduled</div>
        </div>
      </div>

      {/* Country heatmap */}
      <div className="panel">
        <div className="panel-h">
          <span>STORAGE FULLNESS BY COUNTRY · D-1</span>
          <span className="ts">sorted by % full</span>
        </div>
        <div className="heat">
          {sorted.map((r) => (
            <div key={r.country} className="cell">
              <div className="c">{r.country}</div>
              <div className="p" style={{ color: colorFor(r.full_pct) }}>
                {r.full_pct === null ? "—" : `${r.full_pct.toFixed(1)}%`}
              </div>
              <div className="d">
                {r.gas_in_storage_twh != null ? `${r.gas_in_storage_twh.toFixed(1)} / ${r.working_gas_volume_twh?.toFixed(0) ?? "?"} TWh` : "—"}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid c-2">
        {/* Top flows */}
        <div className="panel">
          <div className="panel-h"><span>TOP X-BORDER FLOWS · D-1</span><span className="ts">net direction</span></div>
          <table>
            <thead>
              <tr><th>From</th><th>To</th><th>GWh/d</th></tr>
            </thead>
            <tbody>
              {flows.slice(0, 12).map((f, i) => (
                <tr key={i}>
                  <td className="amber">{f.from}</td>
                  <td>{f.to}</td>
                  <td>{(Math.abs(f.net_kwh) / 1e6).toFixed(0)}</td>
                </tr>
              ))}
              {flows.length === 0 && <tr><td colSpan={3} style={{ color: "var(--fg-mute)" }}>No flow data</td></tr>}
            </tbody>
          </table>
        </div>

        {/* LNG sendout per country */}
        <div className="panel">
          <div className="panel-h"><span>LNG SENDOUT · BY COUNTRY · D-1</span><span className="ts">GWh/d</span></div>
          <table>
            <thead>
              <tr><th>Country</th><th>Sendout</th><th>Inventory</th><th>DTMI</th></tr>
            </thead>
            <tbody>
              {lng
                .filter((r) => (r.sendout_gwh ?? 0) > 0)
                .sort((a, b) => (b.sendout_gwh ?? 0) - (a.sendout_gwh ?? 0))
                .slice(0, 12)
                .map((r, i) => (
                  <tr key={i}>
                    <td className="amber">{r.terminal_id.replace("-AGG", "")}</td>
                    <td>{r.sendout_gwh?.toFixed(0)}</td>
                    <td>{r.inventory_gwh?.toFixed(0)}</td>
                    <td>{r.dtmi_gwh?.toFixed(0) ?? "—"}</td>
                  </tr>
                ))}
              {lng.length === 0 && <tr><td colSpan={4} style={{ color: "var(--fg-mute)" }}>No LNG data</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
