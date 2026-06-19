"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type StorageRow = { date: string; country: string };
type FlowResp = { from_date?: string; to_date?: string; arcs?: unknown[] };

function gasDay(): string {
  // Gas day starts 06:00 UTC. Before 06:00 UTC, gas day is the previous calendar day.
  const now = new Date();
  const utc = new Date(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), now.getUTCHours());
  if (utc.getUTCHours() < 6) {
    utc.setUTCDate(utc.getUTCDate() - 1);
  }
  return utc.toISOString().slice(0, 10);
}

function fmtAge(iso: string | null): string {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  const dh = Math.round((Date.now() - t) / 3_600_000);
  if (Math.abs(dh) < 24) return `${dh}h ago`;
  const dd = Math.round(dh / 24);
  return `${dd}d ago`;
}

export default function StatusBar() {
  const [latest, setLatest] = useState<{ agsi: string | null; entsog: string | null }>({ agsi: null, entsog: null });

  useEffect(() => {
    let alive = true;
    const fetch = async () => {
      try {
        const [storage, flows] = await Promise.all([
          api<StorageRow[]>("/api/storage/country?days=2").catch(() => [] as StorageRow[]),
          api<FlowResp>("/api/flows/arcs?days=1&min_gwh=1").catch(() => ({} as FlowResp)),
        ]);
        const agsi = storage.length ? storage[storage.length - 1].date : null;
        const entsog = flows.to_date ?? null;
        if (alive) setLatest({ agsi, entsog });
      } catch {
        /* swallow */
      }
    };
    fetch();
    const id = setInterval(fetch, 300_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div className="status">
      <span className="seg"><span className="k">GAS DAY</span> <span className="v">{gasDay()}</span></span>
      <span className="seg"><span className="k">AGSI</span> <span className="v">{latest.agsi ?? "—"}</span> <span style={{ color: "var(--fg-mute)" }}>({fmtAge(latest.agsi)})</span></span>
      <span className="seg"><span className="k">ENTSOG</span> <span className="v">{latest.entsog ?? "—"}</span> <span style={{ color: "var(--fg-mute)" }}>({fmtAge(latest.entsog)})</span></span>
      <span className="seg right"><span className="k">v</span> <span className="v">0.2</span></span>
    </div>
  );
}
