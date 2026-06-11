import { api, StorageRow, LngRow } from "@/lib/api";

async function getOverview() {
  const [storage, lng] = await Promise.all([
    api<StorageRow[]>("/api/storage/country?days=1").catch(() => [] as StorageRow[]),
    api<LngRow[]>("/api/lng/country?days=1").catch(() => [] as LngRow[]),
  ]);
  return { storage, lng };
}

export default async function Home() {
  const { storage, lng } = await getOverview();
  const euAvg = storage.length ? storage.reduce((s, r) => s + (r.full_pct ?? 0), 0) / storage.length : null;
  const lngTotal = lng.reduce((s, r) => s + (r.sendout_gwh ?? 0), 0);
  return (
    <div className="grid cols-3">
      <div className="card">
        <h2>EU storage (avg %)</h2>
        <div className="big">{euAvg === null ? "—" : `${euAvg.toFixed(1)}%`}</div>
        <div className="sub">Latest country-day average. Target 90% by Nov 1.</div>
      </div>
      <div className="card">
        <h2>LNG sendout (GWh/d)</h2>
        <div className="big">{lngTotal ? lngTotal.toFixed(0) : "—"}</div>
        <div className="sub">Sum across covered country aggregates.</div>
      </div>
      <div className="card">
        <h2>Status</h2>
        <div className="big">Phase 1</div>
        <div className="sub">ingest skeleton up · run scheduled pulls to populate</div>
      </div>
    </div>
  );
}
