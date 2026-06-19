"use client";

import { useEffect, useState, useMemo } from "react";
import Map from "react-map-gl/maplibre";
import { DeckGL } from "@deck.gl/react";
import { ArcLayer } from "@deck.gl/layers";
import "maplibre-gl/dist/maplibre-gl.css";
import { api } from "@/lib/api";

type Arc = {
  ip_id: string;
  name: string;
  from: string;
  to: string;
  from_lonlat: [number, number];
  to_lonlat: [number, number];
  ip_lonlat: [number, number] | null;
  gwh: number;
};
type ArcsResp = { from_date: string; to_date: string; arcs: Arc[] };

const INITIAL_VIEW = { longitude: 10, latitude: 50, zoom: 3.6, pitch: 30, bearing: 0 };
const TILES = "https://tiles.openfreemap.org/styles/dark";

export default function MapPage() {
  const [data, setData] = useState<ArcsResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [days, setDays] = useState(1);

  useEffect(() => {
    api<ArcsResp>(`/api/flows/arcs?days=${days}&min_gwh=20`)
      .then(setData)
      .catch((e) => setErr(String(e)));
  }, [days]);

  const maxGwh = useMemo(
    () => (data?.arcs?.length ? Math.max(...data.arcs.map((a) => a.gwh)) : 1),
    [data]
  );

  const arcLayer = useMemo(
    () =>
      new ArcLayer<Arc>({
        id: "flow-arcs",
        data: data?.arcs ?? [],
        getSourcePosition: (d) => d.from_lonlat,
        getTargetPosition: (d) => d.to_lonlat,
        getSourceColor: [255, 153, 0, 220],     // amber (source)
        getTargetColor: [65, 182, 230, 220],    // blue (target)
        getWidth: (d) => 1 + 8 * (d.gwh / maxGwh),
        getHeight: 0.4,
        pickable: true,
      }),
    [data, maxGwh]
  );

  return (
    <div style={{ position: "relative", width: "100%", height: "calc(100vh - 90px)" }}>
      <div style={{ position: "absolute", top: 8, left: 8, zIndex: 10, width: 280 }} className="panel">
        <div className="panel-h"><span>CROSS-BORDER FLOWS</span><span className="badge">MAP</span></div>
        <div style={{ fontSize: 11, color: "var(--fg-dim)" }}>
          {data ? `${data.from_date} → ${data.to_date}` : "loading…"}
        </div>
        <div style={{ fontSize: 11, color: "var(--fg-dim)", marginTop: 2 }}>
          {data?.arcs?.length ?? 0} arcs · threshold ≥20 GWh
        </div>
        <div style={{ marginTop: 8, fontSize: 11 }}>
          <span style={{ color: "var(--blue)" }}>WINDOW</span>{" "}
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={1}>1d</option>
            <option value={3}>3d</option>
            <option value={7}>7d</option>
            <option value={14}>14d</option>
          </select>
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: "var(--fg-mute)" }}>
          <span style={{ color: "var(--amber)" }}>●</span> source &nbsp;
          <span style={{ color: "var(--blue)" }}>●</span> destination
        </div>
        {err && <div style={{ color: "var(--red)", marginTop: 6 }}>{err}</div>}
      </div>

      <DeckGL initialViewState={INITIAL_VIEW} controller={true} layers={[arcLayer]}>
        <Map mapStyle={TILES} reuseMaps style={{ width: "100%", height: "100%" }} />
      </DeckGL>

      <div style={{ position: "absolute", right: 8, bottom: 30, zIndex: 10, width: 280, maxHeight: 360, overflow: "auto" }} className="panel">
        <div className="panel-h"><span>TOP 15 ARCS</span><span className="ts">GWh/d</span></div>
        <table>
          <thead>
            <tr><th>Pair</th><th>GWh</th></tr>
          </thead>
          <tbody>
            {(data?.arcs ?? []).slice(0, 15).map((a) => (
              <tr key={a.ip_id}>
                <td><span className="amber">{a.from}</span> → {a.to}</td>
                <td>{a.gwh.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
