"use client";

import { useEffect, useState, useMemo } from "react";
import Map, { Source, Layer } from "react-map-gl/maplibre";
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

const INITIAL_VIEW = {
  longitude: 10,
  latitude: 50,
  zoom: 3.6,
  pitch: 30,
  bearing: 0,
};

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
        getSourceColor: [124, 196, 255, 220],
        getTargetColor: [255, 107, 107, 220],
        getWidth: (d) => 1 + 8 * (d.gwh / maxGwh),
        getHeight: 0.4,
        pickable: true,
      }),
    [data, maxGwh]
  );

  return (
    <div style={{ position: "relative", width: "100%", height: "calc(100vh - 120px)" }}>
      <div style={{ position: "absolute", top: 12, left: 12, zIndex: 10 }} className="card">
        <h2 style={{ marginBottom: 8 }}>Cross-border flows</h2>
        <div className="sub" style={{ marginBottom: 8 }}>
          {data ? `${data.from_date} → ${data.to_date}` : "loading…"} · {data?.arcs?.length ?? 0} arcs · ≥20 GWh
        </div>
        <label style={{ fontSize: 12 }}>
          Days window:
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            style={{ marginLeft: 6, background: "#11151b", color: "#e8eaed", border: "1px solid #1f2933" }}
          >
            <option value={1}>1d</option>
            <option value={3}>3d</option>
            <option value={7}>7d</option>
            <option value={14}>14d</option>
          </select>
        </label>
        {err && <div style={{ color: "#ff6b6b", marginTop: 6 }}>{err}</div>}
      </div>

      <DeckGL initialViewState={INITIAL_VIEW} controller={true} layers={[arcLayer]}>
        <Map mapStyle={TILES} reuseMaps style={{ width: "100%", height: "100%" }} />
      </DeckGL>

      <div style={{ position: "absolute", right: 12, bottom: 12, zIndex: 10 }} className="card">
        <h2>Top arcs</h2>
        <table>
          <thead>
            <tr><th>From → To</th><th>GWh</th></tr>
          </thead>
          <tbody>
            {(data?.arcs ?? []).slice(0, 10).map((a) => (
              <tr key={a.ip_id}>
                <td>{a.from} → {a.to}</td>
                <td>{a.gwh.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
