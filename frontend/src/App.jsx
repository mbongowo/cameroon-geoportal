import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const CAMEROON_CENTER = [12.35, 7.37];

// --- tile URL helpers --------------------------------------------------------
// The API embeds the titiler render hint (rescale + colormap, per layer) in the
// tilejson URL, so the frontend uses it as-is.
function rasterTileJson(item) {
  return item.tiles.tilejson;
}

const VECTOR_PAINT = {
  transport: { "line-color": "#ef4444", "line-width": 0.8 },
  boundaries: { "line-color": "#6d28d9", "line-width": 1.0 },
};

function bboxPolygon(a, b) {
  const minX = Math.min(a.lng, b.lng);
  const maxX = Math.max(a.lng, b.lng);
  const minY = Math.min(a.lat, b.lat);
  const maxY = Math.max(a.lat, b.lat);
  return {
    type: "Polygon",
    coordinates: [[
      [minX, minY], [maxX, minY], [maxX, maxY], [minX, maxY], [minX, minY],
    ]],
  };
}

export default function App() {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const addedRef = useRef({}); // item.id -> [{source, layer}]
  const drawingRef = useRef(false);
  const firstPtRef = useRef(null);

  const [layers, setLayers] = useState([]);
  const [activeIds, setActiveIds] = useState(() => new Set());
  const [aoi, setAoi] = useState(null);
  const [drawing, setDrawing] = useState(false);
  const [exportLayerId, setExportLayerId] = useState("");
  const [format, setFormat] = useState("geotiff");
  const [job, setJob] = useState(null); // {state, result, error}

  // --- map init ---
  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: CAMEROON_CENTER,
      zoom: 5,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.addControl(new maplibregl.ScaleControl(), "bottom-left");
    map.on("click", (e) => {
      if (!drawingRef.current) return;
      if (!firstPtRef.current) {
        firstPtRef.current = e.lngLat;
        return;
      }
      const poly = bboxPolygon(firstPtRef.current, e.lngLat);
      firstPtRef.current = null;
      drawingRef.current = false;
      setDrawing(false);
      setAoi(poly);
      drawAoi(map, poly);
    });
    mapRef.current = map;
    return () => map.remove();
  }, []);

  // --- load catalog ---
  useEffect(() => {
    fetch(`${API_BASE}/search`)
      .then((r) => r.json())
      .then((d) => {
        const items = d.items || [];
        setLayers(items);
        if (items.length) setExportLayerId(items[0].id);
      })
      .catch(() => setLayers([]));
  }, []);

  // keep format valid for the chosen export layer
  useEffect(() => {
    const layer = layers.find((l) => l.id === exportLayerId);
    if (!layer) return;
    setFormat(layer.datatype === "raster" ? "geotiff" : "geojson");
  }, [exportLayerId, layers]);

  function drawAoi(map, poly) {
    const data = { type: "Feature", properties: {}, geometry: poly };
    if (map.getSource("aoi")) {
      map.getSource("aoi").setData(data);
    } else {
      map.addSource("aoi", { type: "geojson", data });
      map.addLayer({ id: "aoi-fill", type: "fill", source: "aoi", paint: { "fill-color": "#2563eb", "fill-opacity": 0.12 } });
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#2563eb", "line-width": 2, "line-dasharray": [2, 1] } });
    }
  }

  function clearAoi() {
    const map = mapRef.current;
    setAoi(null);
    if (map.getLayer("aoi-fill")) map.removeLayer("aoi-fill");
    if (map.getLayer("aoi-line")) map.removeLayer("aoi-line");
    if (map.getSource("aoi")) map.removeSource("aoi");
  }

  function startDraw() {
    firstPtRef.current = null;
    drawingRef.current = true;
    setDrawing(true);
  }

  // --- layer toggle ---
  function addToMap(item) {
    const map = mapRef.current;
    const added = [];
    if (item.datatype === "raster") {
      const source = `src-${item.id}`;
      const layer = `lyr-${item.id}`;
      map.addSource(source, { type: "raster", url: rasterTileJson(item), tileSize: 256, attribution: item.attribution });
      map.addLayer({ id: layer, type: "raster", source, paint: { "raster-opacity": 0.85 } });
      added.push({ source, layer });
    } else if (item.datatype === "vector") {
      const paint = VECTOR_PAINT[item.theme] || { "line-color": "#0ea5e9", "line-width": 1 };
      for (const s of item.tiles.sources || []) {
        const source = `src-${item.id}-${s.id}`;
        const layer = `lyr-${item.id}-${s.id}`;
        map.addSource(source, { type: "vector", url: s.tilejson, attribution: item.attribution });
        map.addLayer({ id: layer, type: "line", source, "source-layer": s.id, paint });
        added.push({ source, layer });
      }
    }
    addedRef.current[item.id] = added;
  }

  function removeFromMap(item) {
    const map = mapRef.current;
    for (const { source, layer } of addedRef.current[item.id] || []) {
      if (map.getLayer(layer)) map.removeLayer(layer);
      if (map.getSource(source)) map.removeSource(source);
    }
    delete addedRef.current[item.id];
  }

  function toggleLayer(item) {
    const next = new Set(activeIds);
    if (next.has(item.id)) {
      next.delete(item.id);
      removeFromMap(item);
    } else {
      next.add(item.id);
      addToMap(item);
    }
    setActiveIds(next);
  }

  // --- export ---
  async function runExport() {
    if (!aoi) return;
    setJob({ state: "PENDING" });
    try {
      const res = await fetch(`${API_BASE}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ layer_id: exportLayerId, aoi, format }),
      }).then((r) => r.json());
      const taskId = res.task_id;
      for (let i = 0; i < 90; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const p = await fetch(`${API_BASE}/export/${taskId}`).then((r) => r.json());
        if (p.state === "SUCCESS") { setJob({ state: "SUCCESS", result: p.result }); return; }
        if (p.state === "FAILURE") { setJob({ state: "FAILURE", error: p.error }); return; }
        setJob({ state: p.state });
      }
      setJob({ state: "TIMEOUT" });
    } catch (e) {
      setJob({ state: "FAILURE", error: String(e) });
    }
  }

  const exportLayer = layers.find((l) => l.id === exportLayerId);
  const formatOptions = exportLayer?.datatype === "raster"
    ? ["geotiff"]
    : ["geojson", "geopackage"];

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <aside style={{ width: 340, padding: 16, overflowY: "auto", borderRight: "1px solid #ddd", boxSizing: "border-box" }}>
        <h1 style={{ fontSize: 18, margin: "0 0 4px" }}>🇨🇲 Cameroon Geoportal</h1>
        <p style={{ fontSize: 12, color: "#666", marginTop: 0 }}>
          License-clear geospatial data. Every layer shows its license &amp; attribution.
        </p>

        <h2 style={{ fontSize: 14 }}>Layers ({layers.length})</h2>
        {layers.length === 0 && <p style={{ fontSize: 12 }}>Loading… (is the API running?)</p>}
        {layers.map((l) => (
          <div key={l.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 10, marginBottom: 8 }}>
            <label style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer" }}>
              <input type="checkbox" checked={activeIds.has(l.id)} onChange={() => toggleLayer(l)} style={{ marginTop: 3 }} />
              <span style={{ flex: 1 }}>
                <strong style={{ fontSize: 13 }}>{l.title}</strong>
                <div style={{ fontSize: 11, color: "#888" }}>{l.theme} · {l.datatype}</div>
                <span style={{ display: "inline-block", marginTop: 6, fontSize: 10, padding: "2px 6px", borderRadius: 4, background: l.tier === "osm-odbl" ? "#fde68a" : "#dcfce7" }}>
                  {l.license}{l.tier === "osm-odbl" ? " · ODbL share-alike" : ""}
                </span>
                <div style={{ fontSize: 10, color: "#999", marginTop: 4 }}>{l.attribution}</div>
              </span>
            </label>
          </div>
        ))}

        <h2 style={{ fontSize: 14, marginTop: 20 }}>Export an area</h2>
        <div style={{ fontSize: 12, color: "#555" }}>
          <ol style={{ paddingLeft: 18, margin: "4px 0" }}>
            <li>Click <em>Draw AOI</em>, then click two corners on the map.</li>
            <li>Pick a layer &amp; format, then export.</li>
          </ol>
          <div style={{ display: "flex", gap: 8, margin: "8px 0" }}>
            <button onClick={startDraw} disabled={drawing} style={btn(drawing)}>
              {drawing ? "Click 2 corners…" : "Draw AOI"}
            </button>
            <button onClick={clearAoi} disabled={!aoi} style={btn(!aoi)}>Clear</button>
          </div>
          <div style={{ fontSize: 11, color: aoi ? "#16a34a" : "#999" }}>
            {aoi ? "✓ AOI selected" : "No AOI yet"}
          </div>

          <label style={lbl}>Layer
            <select value={exportLayerId} onChange={(e) => setExportLayerId(e.target.value)} style={sel}>
              {layers.map((l) => <option key={l.id} value={l.id}>{l.title}</option>)}
            </select>
          </label>
          <label style={lbl}>Format
            <select value={format} onChange={(e) => setFormat(e.target.value)} style={sel}>
              {formatOptions.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>

          <button onClick={runExport} disabled={!aoi || (job && job.state !== "SUCCESS" && job.state !== "FAILURE" && job.state !== "TIMEOUT")} style={{ ...btn(!aoi), width: "100%", marginTop: 10, background: "#2563eb", color: "#fff", borderColor: "#2563eb" }}>
            Export &amp; download
          </button>

          {job && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              {job.state !== "SUCCESS" && job.state !== "FAILURE" && job.state !== "TIMEOUT" && <span>Processing… ({job.state})</span>}
              {job.state === "TIMEOUT" && <span style={{ color: "#b45309" }}>Timed out — try a smaller area.</span>}
              {job.state === "FAILURE" && <span style={{ color: "#dc2626" }}>Failed: {job.error}</span>}
              {job.state === "SUCCESS" && (
                <div>
                  <a href={`${API_BASE}${job.result.download_path}`} style={{ color: "#2563eb", fontWeight: 600 }}>
                    ⬇ Download {job.result.format} bundle
                  </a>
                  <div style={{ color: "#16a34a", marginTop: 4 }}>Includes LICENSE.txt + ATTRIBUTION.txt</div>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
      <main ref={mapContainer} style={{ flex: 1 }} />
    </div>
  );
}

const btn = (disabled) => ({
  fontSize: 12, padding: "6px 10px", borderRadius: 6,
  border: "1px solid #cbd5e1", background: "#fff",
  cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1,
});
const lbl = { display: "block", fontSize: 12, color: "#374151", marginTop: 10 };
const sel = { display: "block", width: "100%", marginTop: 4, padding: 6, fontSize: 12 };
