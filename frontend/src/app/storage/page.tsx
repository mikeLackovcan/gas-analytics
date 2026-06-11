"use client";

import { useEffect, useState } from "react";
import { api, StorageRow } from "@/lib/api";

export default function StoragePage() {
  const [rows, setRows] = useState<StorageRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<StorageRow[]>("/api/storage/country?days=1")
      .then(setRows)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="grid">
      <div className="card">
        <h2>AGSI · country fullness (latest)</h2>
        {err && <div style={{ color: "#ff6b6b" }}>{err}</div>}
        {!rows && !err && <div>loading…</div>}
        {rows && rows.length === 0 && <div className="sub">No data — run AGSI ingest with x-key set in .env.</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Country</th>
                <th>Full %</th>
                <th>Working TWh</th>
                <th>Injection GWh</th>
                <th>Withdrawal GWh</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.country}</td>
                  <td>{r.full_pct?.toFixed(1) ?? "—"}</td>
                  <td>{r.working_gas_twh?.toFixed(1) ?? "—"}</td>
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
