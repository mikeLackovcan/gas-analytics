"use client";

import { useEffect, useState } from "react";
import { api, ForecastPoint } from "@/lib/api";

type ForecastResp = { run_ts: string | null; horizon_days: number; series: ForecastPoint[] };

export default function DemandPage() {
  const [data, setData] = useState<ForecastResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<ForecastResp>("/api/demand/forecast?country=DE&horizon_days=10")
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="grid">
      <div className="card">
        <h2>Demand forecast · DE · D+1..D+10</h2>
        <div className="sub">Run ts: {data?.run_ts ?? "—"} · model lands in Phase 2 (LDZ HDD), Phase 3 (+ power, industrial).</div>
        {err && <div style={{ color: "#ff6b6b" }}>{err}</div>}
        {data && data.series.length === 0 && <div className="sub">No forecast persisted yet.</div>}
        {data && data.series.length > 0 && (
          <table>
            <thead>
              <tr><th>Date</th><th>P10</th><th>P50 (GWh)</th><th>P90</th><th>Model</th></tr>
            </thead>
            <tbody>
              {data.series.map((p, i) => (
                <tr key={i}>
                  <td>{p.target_date}</td>
                  <td>{p.p10?.toFixed(0)}</td>
                  <td>{p.gwh?.toFixed(0)}</td>
                  <td>{p.p90?.toFixed(0)}</td>
                  <td>{p.model_version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
