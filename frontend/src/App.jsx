import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Cameroon bounding box (approx) for the initial map view.
const CAMEROON_CENTER = [12.35, 7.37];

export default function App() {
  const mapContainer = useRef(null);
  const [layers, setLayers] = useState([]);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: CAMEROON_CENTER,
      zoom: 5,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    return () => map.remove();
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/search`)
      .then((r) => r.json())
      .then((d) => setLayers(d.items || []))
      .catch(() => setLayers([]));
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <aside style={{ width: 320, padding: 16, overflowY: "auto", borderRight: "1px solid #ddd" }}>
        <h1 style={{ fontSize: 18 }}>🇨🇲 Cameroon Geoportal</h1>
        <p style={{ fontSize: 12, color: "#666" }}>
          License-clear geospatial data. Every layer shows its license &amp; attribution.
        </p>
        <h2 style={{ fontSize: 14 }}>Catalog ({layers.length})</h2>
        {layers.length === 0 && <p style={{ fontSize: 12 }}>Loading… (start the API)</p>}
        {layers.map((l) => (
          <div key={l.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, marginBottom: 8 }}>
            <strong style={{ fontSize: 13 }}>{l.title}</strong>
            <div style={{ fontSize: 11, color: "#888" }}>{l.theme} · {l.type}</div>
            <span
              style={{
                display: "inline-block",
                marginTop: 6,
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: 4,
                background: l.tier === "osm-odbl" ? "#fde68a" : "#dcfce7",
              }}
            >
              {l.license}
            </span>
            <div style={{ fontSize: 10, color: "#999", marginTop: 4 }}>{l.attribution}</div>
          </div>
        ))}
      </aside>
      <main ref={mapContainer} style={{ flex: 1 }} />
    </div>
  );
}
