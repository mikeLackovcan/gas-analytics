"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const NAV = [
  { href: "/",           mnem: "OVW", label: "Overview" },
  { href: "/map",        mnem: "MAP", label: "Flow Map" },
  { href: "/storage",    mnem: "STO", label: "Storage" },
  { href: "/facilities", mnem: "FAC", label: "Facilities" },
  { href: "/lng",        mnem: "LNG", label: "LNG" },
  { href: "/demand",     mnem: "DEM", label: "Demand" },
];

type StorageRow = { country: string; full_pct: number | null };
type LngRow = { terminal_id: string; sendout_gwh: number | null };
type Price = { hub: string; settle_eur_mwh: number; contract: string };

function Clock() {
  const [t, setT] = useState<string>("--:--:-- UTC");
  useEffect(() => {
    const upd = () => {
      const d = new Date();
      const hh = String(d.getUTCHours()).padStart(2, "0");
      const mm = String(d.getUTCMinutes()).padStart(2, "0");
      const ss = String(d.getUTCSeconds()).padStart(2, "0");
      setT(`${hh}:${mm}:${ss} UTC`);
    };
    upd();
    const id = setInterval(upd, 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="clock">{t}</span>;
}

export default function TopBar() {
  const pathname = usePathname();
  const [tickers, setTickers] = useState<{ lbl: string; val: string; chg?: number }[]>([]);

  useEffect(() => {
    let alive = true;
    const fetchTickers = async () => {
      try {
        const [storage, lng, prices] = await Promise.all([
          api<StorageRow[]>("/api/storage/country?days=1").catch(() => [] as StorageRow[]),
          api<LngRow[]>("/api/lng/country?days=1").catch(() => [] as LngRow[]),
          api<Price[]>("/api/prices/latest").catch(() => [] as Price[]),
        ]);
        const euAvg = storage.length
          ? storage.reduce((s, r) => s + (r.full_pct ?? 0), 0) / storage.length
          : null;
        const lngTotal = lng.reduce((s, r) => s + (r.sendout_gwh ?? 0), 0);
        const ttf = prices.find((p) => p.hub === "TTF" && p.contract === "M+1");
        const the = prices.find((p) => p.hub === "THE" && p.contract === "M+1");
        const peg = prices.find((p) => p.hub === "PEG" && p.contract === "M+1");
        const next: { lbl: string; val: string }[] = [];
        if (ttf) next.push({ lbl: "TTF", val: `${ttf.settle_eur_mwh.toFixed(2)} €/MWh` });
        if (the) next.push({ lbl: "THE", val: `${the.settle_eur_mwh.toFixed(2)}` });
        if (peg) next.push({ lbl: "PEG", val: `${peg.settle_eur_mwh.toFixed(2)}` });
        if (euAvg !== null) next.push({ lbl: "EU STO", val: `${euAvg.toFixed(1)}%` });
        if (lngTotal > 0) next.push({ lbl: "LNG SEND", val: `${lngTotal.toFixed(0)} GWh/d` });
        if (alive) setTickers(next);
      } catch {
        /* swallow */
      }
    };
    fetchTickers();
    const id = setInterval(fetchTickers, 60_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <>
      <div className="ticker">
        <span className="brand">GAS-ANAL</span>
        {tickers.length === 0 && <span style={{ color: "var(--fg-mute)" }}>loading market data…</span>}
        {tickers.map((t, i) => (
          <span key={i} className="tick">
            <span className="lbl">{t.lbl}</span>
            <span className="val">{t.val}</span>
          </span>
        ))}
        <Clock />
      </div>
      <nav className="nav">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href} className={pathname === n.href ? "active" : ""}>
            <span className="mnem">{n.mnem}</span>
            <span>{n.label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
