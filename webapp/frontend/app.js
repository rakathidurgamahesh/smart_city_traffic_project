const API = "/api";
const LEVEL_COLOR = { LOW: "#22c55e", MODERATE: "#eab308", HIGH: "#f97316", SEVERE: "#ef4444", UNKNOWN: "#475569" };

let volumeChart = null;
let lastGraphData = null; // {nodes, edges} — cached so route results can re-draw with a highlighted path

// ---------------------------------------------------------------- summary

async function loadSummary() {
  const res = await fetch(`${API}/summary`);
  const data = await res.json();
  document.getElementById("stat-roads").textContent = data.roads;
  document.getElementById("stat-sensors").textContent = data.sensors;
  document.getElementById("stat-readings").textContent = data.readings;
  document.getElementById("last-updated").textContent = data.last_forecast_at
    ? `Forecast last generated: ${data.last_forecast_at}`
    : "No forecast generated yet";
}

// ---------------------------------------------------------------- volume chart

async function loadVolumeChart() {
  const res = await fetch(`${API}/aggregate/volume`);
  const rows = await res.json();

  const canvas = document.getElementById("volume-chart");

  // Chart.js loads from a CDN — if the browser has no internet access (or a
  // firewall blocks cdnjs.cloudflare.com), fall back to a plain text list
  // instead of crashing the rest of the dashboard's startup sequence.
  if (typeof Chart === "undefined") {
    const fallback = document.createElement("div");
    fallback.className = "muted";
    fallback.innerHTML = "Chart library didn't load (no internet access to the CDN?). Raw data:<br>" +
      rows.map(r => `${r.road_name}: ${r.avg_volume}`).join("<br>");
    canvas.replaceWith(fallback);
    return;
  }

  const ctx = canvas.getContext("2d");
  const labels = rows.map(r => r.road_name);
  const values = rows.map(r => r.avg_volume);

  if (volumeChart) {
    volumeChart.data.labels = labels;
    volumeChart.data.datasets[0].data = values;
    volumeChart.update();
    return;
  }

  volumeChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Avg vehicles / reading", data: values, backgroundColor: "#38bdf8" }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
        y: { ticks: { color: "#94a3b8" }, grid: { color: "#334155" } },
      },
    },
  });
}

// ---------------------------------------------------------------- hotspots table

async function loadHotspots() {
  const res = await fetch(`${API}/forecast/hotspots`);
  const rows = await res.json();
  const tbody = document.querySelector("#hotspots-table tbody");
  tbody.innerHTML = "";

  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="muted">No forecast data yet — click "Re-run forecast" above.</td></tr>`;
    return;
  }

  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${r.road_name}</td>
      <td>${String(r.hour_of_day).padStart(2, "0")}:00</td>
      <td>${r.predicted_volume}</td>
      <td><span class="badge ${r.congestion_level}">${r.congestion_level}</span></td>
    `;
    tbody.appendChild(tr);
  }
}

// ---------------------------------------------------------------- network diagram

function circularLayout(nodes, width, height) {
  const cx = width / 2, cy = height / 2, r = Math.min(width, height) / 2 - 40;
  const positions = {};
  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    positions[node] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });
  return positions;
}

function drawNetwork(graphData, highlightEdgeRoadIds = new Set()) {
  const svg = document.getElementById("network-svg");
  const width = 520, height = 260;
  const positions = circularLayout(graphData.nodes, width, height);

  let svgContent = "";

  for (const edge of graphData.edges) {
    const a = positions[edge.source], b = positions[edge.target];
    const isHighlighted = highlightEdgeRoadIds.has(edge.road_id);
    const color = isHighlighted ? "#38bdf8" : (LEVEL_COLOR[edge.congestion_level] || LEVEL_COLOR.UNKNOWN);
    const width_ = isHighlighted ? 4 : 2.5;
    svgContent += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"
                     stroke="${color}" stroke-width="${width_}">
                     <title>${edge.road_name} (${edge.congestion_level})</title>
                   </line>`;
    const midX = (a.x + b.x) / 2, midY = (a.y + b.y) / 2;
    svgContent += `<text x="${midX}" y="${midY - 4}" fill="#94a3b8" font-size="9" text-anchor="middle">${edge.road_name}</text>`;
  }

  for (const node of graphData.nodes) {
    const p = positions[node];
    svgContent += `<circle cx="${p.x}" cy="${p.y}" r="14" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>`;
    svgContent += `<text x="${p.x}" y="${p.y + 4}" fill="#e2e8f0" font-size="11" text-anchor="middle">${node}</text>`;
  }

  svg.innerHTML = svgContent;
}

async function loadGraph(hour) {
  const res = await fetch(`${API}/graph?hour=${hour}`);
  const data = await res.json();
  lastGraphData = data;
  drawNetwork(data);
  return data;
}

// ---------------------------------------------------------------- route + reading form data

async function populateNodeDropdowns(nodes) {
  const fromSel = document.getElementById("route-from");
  const toSel = document.getElementById("route-to");
  fromSel.innerHTML = nodes.map(n => `<option value="${n}">${n}</option>`).join("");
  toSel.innerHTML = nodes.map(n => `<option value="${n}">${n}</option>`).join("");
  if (nodes.length > 1) toSel.selectedIndex = 1;
}

async function populateRoadDropdown() {
  const res = await fetch(`${API}/roads`);
  const roads = await res.json();
  const sel = document.getElementById("reading-road");
  sel.innerHTML = roads.map(r => `<option value="${r.road_id}">${r.road_name}</option>`).join("");
  await populateSensorDropdown(roads[0]?.road_id);
}

async function populateSensorDropdown(roadId) {
  if (!roadId) return;
  const res = await fetch(`${API}/sensors?road_id=${roadId}`);
  const sensors = await res.json();
  const sel = document.getElementById("reading-sensor");
  sel.innerHTML = sensors.map(s => `<option value="${s.sensor_id}">#${s.sensor_id} — ${s.location_desc}</option>`).join("");
}

// ---------------------------------------------------------------- event wiring

function wireEvents() {
  const hourSlider = document.getElementById("graph-hour");
  hourSlider.addEventListener("input", async () => {
    document.getElementById("graph-hour-label").textContent = `${String(hourSlider.value).padStart(2, "0")}:00`;
    await loadGraph(hourSlider.value);
  });

  document.getElementById("reading-road").addEventListener("change", (e) => {
    populateSensorDropdown(e.target.value);
  });

  document.getElementById("route-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const from = document.getElementById("route-from").value;
    const to = document.getElementById("route-to").value;
    const hour = document.getElementById("route-hour").value;
    const resultEl = document.getElementById("route-result");
    resultEl.textContent = "Finding route...";
    resultEl.className = "muted";

    const res = await fetch(`${API}/route?from=${from}&to=${to}&hour=${hour}`);
    const data = await res.json();

    if (!res.ok) {
      resultEl.textContent = data.error || "No route found.";
      resultEl.className = "error";
      return;
    }

    resultEl.innerHTML = `Route: <strong>${data.path.join(" → ")}</strong> — effective cost ${data.total_cost}
      <br>${data.segments.map(s => `${s.road_name} (${s.congestion_level})`).join(", ")}`;
    resultEl.className = "success";

    if (lastGraphData) {
      const roadIds = new Set(data.segments.map(s => s.road_id));
      drawNetwork(lastGraphData, roadIds);
    }
  });

  document.getElementById("reading-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const sensor_id = parseInt(document.getElementById("reading-sensor").value, 10);
    const vehicle_count = parseInt(document.getElementById("reading-count").value, 10);
    const avg_speed_kmh = parseFloat(document.getElementById("reading-speed").value);
    const statusEl = document.getElementById("reading-status");

    const res = await fetch(`${API}/readings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sensor_id, vehicle_count, avg_speed_kmh }),
    });
    const data = await res.json();

    if (!res.ok) {
      statusEl.textContent = data.error || "Failed to record reading.";
      statusEl.className = "error";
      return;
    }
    statusEl.textContent = `Recorded reading #${data.reading_id} at ${data.ts}`;
    statusEl.className = "success";
    document.getElementById("reading-form").reset();
    loadSummary();
    loadVolumeChart();
    if (window.refreshExtras) refreshExtras();
  });

  document.getElementById("run-forecast-btn").addEventListener("click", async () => {
    const statusEl = document.getElementById("forecast-status");
    statusEl.textContent = "Running regression...";
    const res = await fetch(`${API}/forecast/run`, { method: "POST" });
    const data = await res.json();
    statusEl.textContent = `Wrote ${data.forecast_rows_written} forecast rows for ${data.roads_processed} roads.`;
    loadSummary();
    loadHotspots();
    loadGraph(document.getElementById("graph-hour").value);
    if (window.refreshExtras) refreshExtras();
  });
}

// ---------------------------------------------------------------- init

async function safeRun(fn, label) {
  try {
    await fn();
  } catch (err) {
    console.error(`Failed to load ${label}:`, err);
  }
}

async function init() {
  wireEvents();
  // Each panel loads independently — one failing (e.g. a blocked CDN, a
  // network hiccup) no longer prevents the others from working.
  await safeRun(loadSummary, "summary");
  await safeRun(loadVolumeChart, "volume chart");
  await safeRun(loadHotspots, "hotspots");

  let graphData = null;
  await safeRun(async () => {
    graphData = await loadGraph(document.getElementById("graph-hour").value);
  }, "network graph");

  if (graphData) {
    await safeRun(() => populateNodeDropdowns(graphData.nodes), "route dropdowns");
  }
  await safeRun(populateRoadDropdown, "reading form dropdowns");
}

init();
