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
      grid: { left: 38, right: 12, top: 28, bottom: 30 },
      tooltip: { trigger: "axis", backgroundColor: "#11161f", borderColor: "#1f2933", textStyle: { color: "#fff", fontFamily: "JetBrains Mono" } },
      legend: { textStyle: { color: "#a8b3bf" }, top: 0, itemHeight: 8, itemWidth: 14 },
      xAxis: { type: "time", axisLabel: { color: "#a8b3bf", fontSize: 10 } },
      yAxis: { type: "value", min: 0, max: 100, axisLabel: { color: "#a8b3bf", fontSize: 10, formatter: "{value}%" } },
      series: [
        { name: "5y P10", type: "line", data: bandDates.map((d, i) => [d, p10[i]]), lineStyle: { opacity: 0 }, symbol: "none", stack: "band-bot" },
        { name: "5y P10-P90", type: "line", data: bandDates.map((d, i) => [d, p90[i] - p10[i]]), lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(65,182,230,0.15)" }, symbol: "none", stack: "band-bot" },
        { name: "5y P50", type: "line", data: bandDates.map((d, i) => [d, p50[i]]), lineStyle: { color: "#41b6e6", type: "dashed", width: 1 }, symbol: "none" },
        { name: "Actual", type: "line", data: actualSeries, lineStyle: { color: "#ff9900", width: 2 }, symbol: "none" },
        { name: "Required→90%", type: "line", data: requiredSeries, lineStyle: { color: "#ff5f5f", width: 1.2, type: "dotted" }, symbol: "none" },
        { name: "90% target", type: "line", markLine: { silent: true, symbol: "none", data: [{ yAxis: 90, lineStyle: { color: "#ff5f5f", type: "dashed" } }] } },
      ],
    };
  }, [traj]);

  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="panel">
        <div className="panel-h">
          <span>STORAGE TRAJECTORY VS NOV-1 TARGET</span>
          <span className="badge">{country}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, marginBottom: 6 }}>
          <span style={{ color: "var(--blue)" }}>COUNTRY</span>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {traj?.current_pct != null && (
            <span>
              <span style={{ color: "var(--blue)" }}>CURRENT</span>{" "}
              <span style={{ color: "var(--amber)", fontWeight: 700 }}>{traj.current_pct.toFixed(1)}%</span>
            </span>
          )}
          {traj?.target_date && (
            <span>
              <span style={{ color: "var(--blue)" }}>DEADLINE</span>{" "}
              <span>{traj.target_date}</span>
            </span>
          )}
        </div>
        {trajOption && (
          <div style={{ height: 340 }}>
            <ReactECharts option={trajOption} style={{ height: "100%", width: "100%" }} theme="dark" />
          </div>
        )}
        {traj && traj.band_by_doy.length === 0 && (
          <div style={{ color: "var(--fg-mute)", fontSize: 11, marginTop: 8 }}>
            No 5y history yet — run <code>python -m app.ingest.backfill_all --years 5</code>.
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-h"><span>AGSI · COUNTRY SNAPSHOT</span><span className="ts">D-1</span></div>
        {!rows && <div style={{ color: "var(--fg-mute)" }}>loading…</div>}
        {rows && rows.length === 0 && <div style={{ color: "var(--fg-mute)" }}>No data.</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Country</th>
                <th>Full %</th>
                <th>Gas (TWh)</th>
                <th>Capacity (TWh)</th>
                <th>Inj (GWh)</th>
                <th>Wdr (GWh)</th>
                <th>Net</th>
              </tr>
            </thead>
            <tbody>
              {rows
                .sort((a, b) => (b.full_pct ?? 0) - (a.full_pct ?? 0))
                .map((r, i) => {
                  const net = (r.injection_gwh ?? 0) - (r.withdrawal_gwh ?? 0);
                  return (
                    <tr key={i}>
                      <td className="amber">{r.country}</td>
                      <td style={{ color: (r.full_pct ?? 0) >= 90 ? "var(--green)" : (r.full_pct ?? 0) < 50 ? "var(--red)" : "var(--fg)" }}>
                        {r.full_pct?.toFixed(1) ?? "—"}
                      </td>
                      <td>{r.gas_in_storage_twh?.toFixed(1) ?? "—"}</td>
                      <td>{r.working_gas_volume_twh?.toFixed(1) ?? "—"}</td>
                      <td>{r.injection_gwh?.toFixed(0) ?? "—"}</td>
                      <td>{r.withdrawal_gwh?.toFixed(0) ?? "—"}</td>
                      <td className={net >= 0 ? "up" : "down"}>{net >= 0 ? "+" : ""}{net.toFixed(0)}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
