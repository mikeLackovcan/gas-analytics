"use client";

import { useEffect, useState, useMemo } from "react";
import TVChart, { TVSeries } from "@/components/TVChart";
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

function doyToDate(doy: number, year: number): string {
  const d = new Date(Date.UTC(year, 0, doy));
  return d.toISOString().slice(0, 10);
}

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

  const seriesData: TVSeries[] = useMemo(() => {
    if (!traj) return [];
    const year = new Date().getFullYear();
    const sort = <T extends { time: string }>(xs: T[]) =>
      xs.slice().sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

    const p10 = sort(traj.band_by_doy.map((b) => ({ time: doyToDate(b.doy, year), value: b.p10 })));
    const p50 = sort(traj.band_by_doy.map((b) => ({ time: doyToDate(b.doy, year), value: b.p50 })));
    const p90 = sort(traj.band_by_doy.map((b) => ({ time: doyToDate(b.doy, year), value: b.p90 })));
    const actual   = sort(traj.actual.map((a) => ({ time: a.date, value: a.pct })));
    const required = sort(traj.required_path.map((r) => ({ time: r.date, value: r.pct })));

    return [
      { id: "p10", type: "area", data: p10,
        topColor: "rgba(0,0,0,0)", bottomColor: "rgba(0,0,0,0)", color: "rgba(0,0,0,0)" },
      { id: "p90", type: "area", data: p90,
        topColor: "rgba(65,182,230,0.18)", bottomColor: "rgba(65,182,230,0.02)", color: "rgba(0,0,0,0)" },
      { id: "p50",      type: "line", data: p50,      color: "#41b6e6", lineWidth: 1, lineStyle: "dashed" },
      { id: "required", type: "line", data: required, color: "#ff5f5f", lineWidth: 1, lineStyle: "dotted" },
      { id: "actual",   type: "line", data: actual,   color: "#ff9900", lineWidth: 2 },
    ];
  }, [traj]);

  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="panel">
        <div className="panel-h">
          <span>STORAGE TRAJECTORY VS NOV-1 TARGET · {country}</span>
          <span className="ts">amber actual · blue 5y P10-P90 · red required-to-90%</span>
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
        {seriesData.length > 0 && (
          <TVChart
            height={360}
            series={seriesData}
            yUnit="%"
            priceLines={[{ price: 90, color: "#ff5f5f", label: "90% target", lineStyle: "dashed" }]}
          />
        )}
        {traj && traj.band_by_doy.length === 0 && (
          <div style={{ color: "var(--fg-mute)", fontSize: 11, marginTop: 8 }}>
            No 5y history yet — backfill more AGSI history to populate the band.
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
                .slice()
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
