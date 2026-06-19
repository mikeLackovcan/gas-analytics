"use client";

import { useEffect, useState } from "react";
import { api, LngRow } from "@/lib/api";

type Slack = {
  country: string;
  date: string;
  sendout_gwh: number;
  inventory_gwh: number;
  capacity_gwh_d: number | null;
  slack_gwh_d: number | null;
  utilization: number | null;
  inventory_days_to_empty: number | null;
};

export default function LngPage() {
  const [rows, setRows] = useState<LngRow[] | null>(null);
  const [slack, setSlack] = useState<Slack[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api<LngRow[]>("/api/lng/country?days=1"),
      api<Slack[]>("/api/lng/slack").catch(() => []),
    ])
      .then(([r, s]) => { setRows(r); setSlack(s); })
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="grid" style={{ gap: 8 }}>
      <div className="panel">
        <div className="panel-h"><span>LNG SLACK · UTILIZATION · INVENTORY DAYS</span><span className="ts">latest</span></div>
        {slack.length === 0 && <div style={{ color: "var(--fg-mute)" }}>No slack data — capacities require manual fill on /about-derived terminals.</div>}
        {slack.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Country</th>
                <th>Date</th>
                <th>Sendout GWh/d</th>
                <th>Capacity GWh/d</th>
                <th>Util %</th>
                <th>Slack GWh/d</th>
                <th>Inv GWh</th>
                <th>Days→empty</th>
              </tr>
            </thead>
            <tbody>
              {slack.map((s, i) => (
                <tr key={i}>
                  <td className="amber">{s.country}</td>
                  <td>{s.date}</td>
                  <td>{s.sendout_gwh.toFixed(0)}</td>
                  <td>{s.capacity_gwh_d?.toFixed(0) ?? "—"}</td>
                  <td>{s.utilization == null ? "—" : (s.utilization * 100).toFixed(0) + "%"}</td>
                  <td>{s.slack_gwh_d?.toFixed(0) ?? "—"}</td>
                  <td>{s.inventory_gwh.toFixed(0)}</td>
                  <td>{s.inventory_days_to_empty?.toFixed(1) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <div className="panel-h"><span>ALSI · COUNTRY AGGREGATES</span><span className="ts">D-1</span></div>
        {err && <div style={{ color: "var(--red)" }}>{err}</div>}
        {!rows && !err && <div style={{ color: "var(--fg-mute)" }}>loading…</div>}
        {rows && rows.length === 0 && <div style={{ color: "var(--fg-mute)" }}>No data.</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Terminal/Country</th>
                <th>Sendout GWh/d</th>
                <th>Inventory GWh</th>
                <th>DTMI GWh</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="amber">{r.terminal_id}</td>
                  <td>{r.sendout_gwh?.toFixed(0) ?? "—"}</td>
                  <td>{r.inventory_gwh?.toFixed(0) ?? "—"}</td>
                  <td>{r.dtmi_gwh?.toFixed(0) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
