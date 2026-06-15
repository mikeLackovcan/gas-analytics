"use client";

import { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
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
      api<NowcastRow[]>(`/api/demand/nowcast?country=${country}&days=60`),
    ])
      .then(([f, a]) => { setFc(f); setActual(a); })
      .catch((e) => setErr(String(e)));
  }, [country]);

  const option = useMemo(() => {
    if (!fc) return null;
    const actualSeries = actual.map((a) => [a.date, a.nowcast_gwh]);
    const p50 = fc.series.map((p) => [p.target_date, p.gwh]);
    const p10 = fc.series.map((p) => [p.target_date, p.p10]);
    const p90 = fc.series.map((p) => [p.target_date, p.p90]);
    const dates = fc.series.map((p) => p.target_date);
    const bandLow = dates.map((d, i) => [d, fc.series[i].p10]);
    const bandSpan = dates.map((d, i) => [d, fc.series[i].p90 - fc.series[i].p10]);
    return {
      backgroundColor: "transparent",
      grid: { left: 60, right: 20, top: 40, bottom: 50 },
      tooltip: { trigger: "axis" },
      legend: { textStyle: { color: "#9aa5b1" }, top: 8 },
      xAxis: { type: "time", axisLabel: { color: "#9aa5b1" } },
      yAxis: { type: "value", axisLabel: { color: "#9aa5b1", formatter: "{value} GWh" } },
      series: [
        { name: "P10", type: "line", data: bandLow, lineStyle: { opacity: 0 }, symbol: "none", stack: "band" },
        { name: "P10-P90", type: "line", data: bandSpan, lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(124,196,255,0.18)" }, symbol: "none", stack: "band" },
        { name: "Nowcast (actual)", type: "line", data: actualSeries, lineStyle: { color: "#ffd166", width: 2.2 }, symbol: "none" },
        { name: "Forecast P50", type: "line", data: p50, lineStyle: { color: "#7cc4ff", width: 2.2 }, symbol: "none" },
      ],
    };
  }, [fc, actual]);

  return (
    <div className="grid">
      <div className="card">
        <h2>Demand · {country} · D+1..D+10</h2>
        <div className="sub">
          Country:
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            style={{ marginLeft: 8, background: "#0e1116", color: "#e8eaed", border: "1px solid #1f2933" }}
          >
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {fc?.run_ts && <span> · run: {fc.run_ts.replace("T", " ")}</span>}
          {fc?.series?.[0]?.model_version && <span> · model: {fc.series[0].model_version}</span>}
        </div>
        {err && <div style={{ color: "#ff6b6b", marginTop: 8 }}>{err}</div>}
        {option && (
          <div style={{ height: 380, marginTop: 12 }}>
            <ReactECharts option={option} style={{ height: "100%", width: "100%" }} />
          </div>
        )}
        {fc && fc.series.length === 0 && (
          <div className="sub" style={{ marginTop: 8 }}>
            No forecast persisted. Trigger:
            <code style={{ marginLeft: 6 }}>POST /api/demand/forecast/refresh</code>
            <br />
            Needs at least ~90d of demand_country_daily + HDD history to fit.
          </div>
        )}
      </div>

      <div className="card">
        <h2>Recent nowcast (mass-balance) — last 14 days</h2>
        {actual.length === 0 && <div className="sub">No nowcast rows yet — run ENTSOG ingest + demand_nowcast.</div>}
        {actual.length > 0 && (
          <table>
            <thead><tr><th>Date</th><th>Demand (GWh)</th><th>Model</th></tr></thead>
            <tbody>
              {actual.slice(-14).reverse().map((a, i) => (
                <tr key={i}>
                  <td>{a.date}</td>
                  <td>{a.nowcast_gwh.toFixed(0)}</td>
                  <td>{a.model_version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
