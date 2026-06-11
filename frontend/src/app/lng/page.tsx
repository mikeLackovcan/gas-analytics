"use client";

import { useEffect, useState } from "react";
import { api, LngRow } from "@/lib/api";

export default function LngPage() {
  const [rows, setRows] = useState<LngRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<LngRow[]>("/api/lng/country?days=1")
      .then(setRows)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="grid">
      <div className="card">
        <h2>ALSI · LNG terminal aggregates (latest)</h2>
        {err && <div style={{ color: "#ff6b6b" }}>{err}</div>}
        {!rows && !err && <div>loading…</div>}
        {rows && rows.length === 0 && <div className="sub">No data — run ALSI ingest with x-key set.</div>}
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
                  <td>{r.terminal_id}</td>
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
