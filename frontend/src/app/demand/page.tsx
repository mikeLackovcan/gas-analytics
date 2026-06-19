"use client";

import { useEffect, useMemo, useState } from "react";
import TVChart, { TVSeries } from "@/components/TVChart";
import { api } from "@/lib/api";

type ForecastPoint = { target_date: string; country: string; gwh: number; p10: number; p90: number; model_version: string };
type ForecastResp = { run_ts: string | null; horizon_days: number; series: ForecastPoint[] };
type NowcastRow = { date: string; country: string; nowcast_gwh: number; model_version: string };

const COUNTRIES = ["DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES"];

export default function DemandPage() {
  const [country, setCountry] = useState("DE");
  const [fc, setFc] = useState<ForecastResp | null>(null);
  const [actual, setActual] = useState<NowcastRow[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setFc(null); setActual([]); setErr(null);
    Promise.all([
      api<ForecastResp>(`/api/demand/forecast?country=${country}&horizon_days=10`),
      api<NowcastRow[]>(`/api/demand/nowcast?country=${country}&days=90`),
    ])
      .then(([f, a]) => { setFc(f); setActual(a); })
      .catch((e) => setErr(String(e)));
  }, [country]);

  const seriesData: TVSeries[] = useMemo(() => {
    if (!fc) return [];
    const sortByTime = <T extends { time: string }>(xs: T[]) =>
      xs.slice().sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));

    const nowcast = sortByTime(actual.map((a) => ({ time: a.date, value: a.nowcast_gwh })));
    const p50    = sortByTime(fc.series.map((p) => ({ time: p.target_date, value: p.gwh })));
    const p10    = sortByTime(fc.series.map((p) => ({ time: p.target_date, value: p.p10 })));
    const p90    = sortByTime(fc.series.map((p) => ({ time: p.target_date, value: p.p90 })));

    return [
      // Lower band (transparent) — for a stacked band visual, we render two area series.
      { id: "p10", type: "area", data: p10,
        topColor: "rgba(0,0,0,0)", bottomColor: "rgba(0,0,0,0)", color: "rgba(0,0,0,0)" },
      { id: "p90", type: "area", data: p90,
        topColor: "rgba(65,182,230,0.20)", bottomColor: "rgba(65,182,230,0.02)", color: "rgba(0,0,0,0)" },
      { id: "nowcast", type: "line", data: nowcast, color: "#ff9900", lineWidth: 2 },
      { id: "p50",     type: "line", data: p50,     color: "#41b6e6", lineWidth: 2 },
    ];
  }, [fc, actual]);

  const lastActual = actual.length ? actual[actual.length - 1] : null;
  const fcTomorrow = fc?.series?.[0];
  const fcMax = fc?.series?.length ? Math.max(...fc.series.map((p) => p.gwh)) : null;

  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="grid c-4">
        <div className="panel kpi">
          <div className="panel-h"><span>LATEST NOWCAST</span><span className="badge">D-1</span></div>
          <div className="big amber">{lastActual ? lastActual.nowcast_gwh.toFixed(0) : "—"}</div>
          <div className="sub">{lastActual?.date ?? "—"} · {country}</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>FCST D+1</span><span className="badge">P50</span></div>
          <div className="big">{fcTomorrow ? fcTomorrow.gwh.toFixed(0) : "—"}</div>
          <div className="sub">{fcTomorrow ? `[${fcTomorrow.p10.toFixed(0)} .. ${fcTomorrow.p90.toFixed(0)}]` : "—"} GWh/d</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>FCST D+10 PEAK</span><span className="badge">P50</span></div>
          <div className="big">{fcMax == null ? "—" : fcMax.toFixed(0)}</div>
          <div className="sub">max across horizon</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>MODEL</span><span className="badge">v0.2</span></div>
          <div className="big" style={{ fontSize: 14 }}>{fc?.series?.[0]?.model_version ?? "—"}</div>
          <div className="sub">run {fc?.run_ts?.replace("T", " ") ?? "—"}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-h">
          <span>DEMAND · NOWCAST + D+1..D+10 FORECAST · {country}</span>
          <span className="ts">amber actual · blue P50 · shaded P10-P90</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, marginBottom: 6 }}>
          <span style={{ color: "var(--blue)" }}>COUNTRY</span>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        {err && <div style={{ color: "var(--red)" }}>{err}</div>}
        {seriesData.length > 0 && <TVChart height={380} series={seriesData} yUnit="GWh" />}
        {fc && fc.series.length === 0 && (
          <div style={{ color: "var(--fg-mute)", fontSize: 11, marginTop: 8 }}>
            No forecast persisted. Trigger: <code>POST /api/demand/forecast/refresh</code>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-h"><span>NOWCAST · LAST 14 DAYS</span><span className="badge">{country}</span></div>
        <table>
          <thead><tr><th>Date</th><th>Demand GWh/d</th><th>Model</th></tr></thead>
          <tbody>
            {actual.slice(-14).reverse().map((a, i) => (
              <tr key={i}>
                <td>{a.date}</td>
                <td>{a.nowcast_gwh.toFixed(0)}</td>
                <td style={{ color: "var(--fg-mute)", fontSize: 10 }}>{a.model_version}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
