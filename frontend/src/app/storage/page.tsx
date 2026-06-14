"use client";

import { useEffect, useState, useMemo } from "react";
import ReactECharts from "echarts-for-react";
import { api, StorageRow } from "@/lib/api";

type Trajectory = {
  country: string;
  target_pct: number;
  target_date: string;
  current_pct: number | null;
  actual: { date: string; pct: number }[];
  band_by_doy: { doy: number; p10: number; p50: number; p90: number }[];
  required_path: { date: string; pct: number }[];
};

const COUNTRIES = ["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"];

export default function StoragePage() {
  const [rows, setRows] = useState<StorageRow[] | null>(null);
  const [country, setCountry] = useState("DE");
  const [traj, setTraj] = useState<Trajectory | null>(null);

  useEffect(() => {
    api<StorageRow[]>("/api/storage/country?days=1").then(setRows).catch(() => setRows([]));
  }, []);

  useEffect(() => {
    api<Trajectory>(`/api/storage/trajectory?country=${country}`).then(setTraj).catch(() => setTraj(null));
  }, [country]);

  const trajOption = useMemo(() => {
    if (!traj) return null;
    const year = new Date().getFullYear();
    const doyToDate = (doy: number) => {
      const d = new Date(year, 0, doy);
      return d.toISOString().slice(0, 10);
    };
    const bandDates = traj.band_by_doy.map((b) => doyToDate(b.doy));
    const p10 = traj.band_by_doy.map((b) => b.p10);
    const p50 = traj.band_by_doy.map((b) => b.p50);
    const p90 = traj.band_by_doy.map((b) => b.p90);
    const actualSeries = traj.actual.map((a) => [a.date, a.pct]);
    const requiredSeries = traj.required_path.map((r) => [r.date, r.pct]);

    return {
      backgroundColor: "transparent",
      grid: { left: 50, right: 20, top: 40, bottom: 40 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "#9aa5b1" }, top: 10 },
      xAxis: { type: "time", axisLabel: { color: "#9aa5b1" } },
      yAxis: { type: "value", min: 0, max: 100, axisLabel: { color: "#9aa5b1", formatter: "{value}%" } },
      series: [
        { name: "5y P10", type: "line", data: bandDates.map((d, i) => [d, p10[i]]), lineStyle: { opacity: 0 }, symbol: "none", stack: "band-bot" },
        { name: "5y P10-P90", type: "line", data: bandDates.map((d, i) => [d, p90[i] - p10[i]]), lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(124,196,255,0.15)" }, symbol: "none", stack: "band-bot" },
        { name: "5y P50", type: "line", data: bandDates.map((d, i) => [d, p50[i]]), lineStyle: { color: "#7cc4ff", type: "dashed", width: 1 }, symbol: "none" },
        { name: "Actual", type: "line", data: actualSeries, lineStyle: { color: "#ffd166", width: 2.5 }, symbol: "none" },
        { name: "Required to 90%", type: "line", data: requiredSeries, lineStyle: { color: "#ff6b6b", width: 1.5, type: "dotted" }, symbol: "none" },
        { name: "90% target", type: "line", markLine: { silent: true, symbol: "none", data: [{ yAxis: 90, lineStyle: { color: "#ff6b6b", type: "dashed" } }] } },
      ],
    };
  }, [traj]);

  return (
    <div className="grid">
      <div className="card">
        <h2>Storage trajectory vs Nov-1 target</h2>
        <div className="sub">
          Country:
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            style={{ marginLeft: 8, background: "#0e1116", color: "#e8eaed", border: "1px solid #1f2933" }}
          >
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {traj?.current_pct != null && <span> · current: <b>{traj.current_pct.toFixed(1)}%</b></span>}
        </div>
        {trajOption && (
          <div style={{ height: 360, marginTop: 12 }}>
            <ReactECharts option={trajOption} style={{ height: "100%", width: "100%" }} />
          </div>
        )}
        {traj && traj.band_by_doy.length === 0 && (
          <div className="sub" style={{ marginTop: 8 }}>
            No 5y history yet — run <code>python -m app.ingest.backfill_all --years 5</code> to populate the band.
          </div>
        )}
      </div>

      <div className="card">
        <h2>AGSI · country fullness (latest)</h2>
        {!rows && <div>loading…</div>}
        {rows && rows.length === 0 && <div className="sub">No data — run AGSI ingest.</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Country</th><th>Full %</th><th>Gas in storage (TWh)</th><th>Working vol (TWh)</th>
                <th>Inj (GWh)</th><th>Wdr (GWh)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.country}</td>
                  <td>{r.full_pct?.toFixed(1) ?? "—"}</td>
                  <td>{r.working_gas_twh?.toFixed(1) ?? "—"}</td>
                  <td>—</td>
                  <td>{r.injection_gwh?.toFixed(0) ?? "—"}</td>
                  <td>{r.withdrawal_gwh?.toFixed(0) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
