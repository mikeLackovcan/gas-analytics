"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";

type Facility = {
  id: string; eic: string; company_eic: string | null; country: string;
  operator: string | null; name: string; type: string | null;
  operational_start_date: string | null; operational_end_date: string | null;
};

const COUNTRIES = ["ALL", "DE", "NL", "FR", "IT", "AT", "CZ", "BE", "PL", "ES", "SK", "HU", "RO", "BG", "DK", "HR", "LV", "PT", "UK"];

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
    <div className="grid" style={{ gap: 8 }}>
      <div className="panel">
        <div className="panel-h"><span>STORAGE FACILITIES · AGSI /about CATALOG</span><span className="badge">{rows?.length ?? 0} active</span></div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11 }}>
          <span style={{ color: "var(--blue)" }}>COUNTRY</span>
          <select value={country} onChange={(e) => setCountry(e.target.value)}>
            {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {country === "ALL" && byCountry.length > 0 && (
        <div className="panel">
          <div className="panel-h"><span>FACILITY COUNT · BY COUNTRY</span><span className="ts">active only</span></div>
          <table>
            <thead><tr><th>Country</th><th>Facilities</th></tr></thead>
            <tbody>
              {byCountry.map(([c, n]) => (
                <tr key={c}><td className="amber">{c}</td><td>{n}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="panel">
        <div className="panel-h"><span>FACILITIES</span><span className="ts">EIC · type · operator</span></div>
        {!rows && <div style={{ color: "var(--fg-mute)" }}>loading…</div>}
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
                  <td className="amber">{r.country}</td>
                  <td>{r.operator ?? "—"}</td>
                  <td>{r.name}</td>
                  <td>{r.type ?? "—"}</td>
                  <td>{r.operational_start_date ?? "—"}</td>
                  <td>{r.operational_end_date ?? "—"}</td>
                  <td style={{ fontSize: 10, color: "var(--fg-mute)" }}>{r.eic}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
