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
    const dates = fc.series.map((p) => p.target_date);
    const bandLow = dates.map((d, i) => [d, fc.series[i].p10]);
    const bandSpan = dates.map((d, i) => [d, fc.series[i].p90 - fc.series[i].p10]);
    return {
      backgroundColor: "transparent",
      grid: { left: 50, right: 12, top: 28, bottom: 30 },
      tooltip: { trigger: "axis", backgroundColor: "#11161f", borderColor: "#1f2933", textStyle: { color: "#fff", fontFamily: "JetBrains Mono" } },
      legend: { textStyle: { color: "#a8b3bf" }, top: 0, itemHeight: 8, itemWidth: 14 },
      xAxis: { type: "time", axisLabel: { color: "#a8b3bf", fontSize: 10 } },
      yAxis: { type: "value", axisLabel: { color: "#a8b3bf", fontSize: 10, formatter: "{value}" }, name: "GWh/d", nameTextStyle: { color: "#41b6e6", fontSize: 10 } },
      series: [
        { name: "P10", type: "line", data: bandLow, lineStyle: { opacity: 0 }, symbol: "none", stack: "band" },
        { name: "P10-P90", type: "line", data: bandSpan, lineStyle: { opacity: 0 }, areaStyle: { color: "rgba(65,182,230,0.18)" }, symbol: "none", stack: "band" },
        { name: "Nowcast", type: "line", data: actualSeries, lineStyle: { color: "#ff9900", width: 2 }, symbol: "none" },
        { name: "Forecast P50", type: "line", data: p50, lineStyle: { color: "#41b6e6", width: 2 }, symbol: "none" },
      ],
    };
  }, [fc, actual]);

  const fcRecent = fc?.series ?? [];
  const lastActual = actual.length ? actual[actual.length - 1] : null;
  const fcTomorrow = fcRecent[0];
  const fcMaxNext10 = fcRecent.length ? Math.max(...fcRecent.map((p) => p.gwh)) : null;

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
          <div className="big">{fcMaxNext10 == null ? "—" : fcMaxNext10.toFixed(0)}</div>
          <div className="sub">max across horizon</div>
        </div>
        <div className="panel kpi">
          <div className="panel-h"><span>MODEL</span><span className="badge">v0.2</span></div>
          <div className="big" style={{ fontSize: 16 }}>{fc?.series?.[0]?.model_version ?? "—"}</div>
          <div className="sub">run {fc?.run_ts?.replace("T", " ") ?? "—"}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-h">
          <span>DEMAND · NOWCAST + D+1..D+10 FORECAST</span>
          <span className="badge">{country}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, marginBottom: 6 }}>
          <span style={{ color: "var(--blue)" }}>COUNTRY</span>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        {err && <div style={{ color: "var(--red)", marginTop: 4 }}>{err}</div>}
        {option && (
          <div style={{ height: 360 }}>
            <ReactECharts option={option} style={{ height: "100%", width: "100%" }} />
          </div>
        )}
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
