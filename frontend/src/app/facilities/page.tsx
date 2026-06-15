"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";

type Facility = {
  id: string; eic: string; company_eic: string | null; country: string;
  operator: string | null; name: string; type: string | null;
  operational_start_date: string | null; operational_end_date: string | null;
};

const COUNTRIES = ["ALL", "DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES", "SK", "HU", "RO", "BG"];

export default function FacilitiesPage() {
  const [rows, setRows] = useState<Facility[] | null>(null);
  const [country, setCountry] = useState("ALL");

  useEffect(() => {
    const q = country === "ALL" ? "" : `?country=${country}`;
    api<Facility[]>(`/api/storage/facilities${q}`).then(setRows).catch(() => setRows([]));
  }, [country]);

  const byCountry = useMemo(() => {
    const m = new Map<string, number>();
    rows?.forEach((r) => m.set(r.country, (m.get(r.country) ?? 0) + 1));
    return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
  }, [rows]);

  return (
    <div className="grid">
      <div className="card">
        <h2>Storage facilities (AGSI /about catalog)</h2>
        <div className="sub">
          Country:
          <select value={country} onChange={(e) => setCountry(e.target.value)}
                  style={{ marginLeft: 8, background: "#0e1116", color: "#e8eaed", border: "1px solid #1f2933" }}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {rows && <span style={{ marginLeft: 12 }}>{rows.length} active facilities</span>}
        </div>
      </div>

      {country === "ALL" && byCountry.length > 0 && (
        <div className="card">
          <h2>Active facility count by country</h2>
          <table>
            <thead><tr><th>Country</th><th>Facilities</th></tr></thead>
            <tbody>
              {byCountry.map(([c, n]) => (<tr key={c}><td>{c}</td><td>{n}</td></tr>))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>Facilities</h2>
        {!rows && <div>loading…</div>}
        {rows && rows.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Country</th><th>Operator</th><th>Facility</th><th>Type</th><th>Start</th><th>End</th><th>EIC</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.eic}>
                  <td>{r.country}</td>
                  <td>{r.operator ?? "—"}</td>
                  <td>{r.name}</td>
                  <td>{r.type ?? "—"}</td>
                  <td>{r.operational_start_date ?? "—"}</td>
                  <td>{r.operational_end_date ?? "—"}</td>
                  <td style={{ fontSize: 11, color: "#7b8794" }}>{r.eic}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
