"use client";

import { useEffect, useState } from "react";
import { api, CountryPairFlow } from "@/lib/api";

export default function MapPage() {
  const [rows, setRows] = useState<CountryPairFlow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<CountryPairFlow[]>("/api/flows/country-pairs?days=1")
      .then(setRows)
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="grid">
      <div className="card">
        <h2>Country-pair flows · last day</h2>
        <div className="sub">Map view (MapLibre + deck.gl arcs) lands once ENTSOG data starts flowing. Table below shows raw aggregate.</div>
      </div>
      <div className="card">
        {err && <div style={{ color: "#ff6b6b" }}>{err}</div>}
        {!rows && !err && <div>loading…</div>}
        {rows && rows.length === 0 && <div className="sub">No flows yet — run the ENTSOG ingest.</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr><th>From</th><th>To</th><th>Net GWh</th></tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>{r.from}</td>
                  <td>{r.to}</td>
                  <td>{(r.net_kwh / 1e6).toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
