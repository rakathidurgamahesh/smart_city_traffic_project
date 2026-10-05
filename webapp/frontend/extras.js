// Extended dashboard panels: KPIs, trend, heatmap, road drill-down, alerts, sensors, live feed.
const COL = { LOW: "#22c55e", MODERATE: "#eab308", HIGH: "#f97316", SEVERE: "#ef4444", SLOW: "#a78bfa", UNKNOWN: "#334155" };
const $ = (id) => document.getElementById(id);
const hh = (h) => `${String(h).padStart(2, "0")}:00`;
const charts = {};
const getJSON = async (u) => (await fetch(u)).json();

function mkChart(id, cfg) {
  if (typeof Chart === "undefined") return;
  if (charts[id]) { charts[id].destroy(); }
  Chart.defaults.color = "#94a3b8";
  charts[id] = new Chart($(id), cfg);
}
const axes = { x: { grid: { color: "#334155" } }, y: { grid: { color: "#334155" } } };

async function loadKpis() {
  const k = await getJSON(`${API}/kpis`);
  $("kpi-index").textContent = k.congestion_index + "%";
  $("kpi-speed").textContent = k.avg_speed ?? "-";
  $("kpi-alerts").textContent = k.alerts;
  $("kpi-busiest").textContent = k.busiest_road ?? "-";
  $("kpi-peak").textContent = k.peak_hour == null ? "-" : hh(k.peak_hour);
  const m = $("kpi-meter");
  m.style.width = k.congestion_index + "%";
  m.style.background = k.congestion_index > 66 ? COL.SEVERE : k.congestion_index > 33 ? COL.MODERATE : COL.LOW;
}

async function loadTrend() {
  const d = await getJSON(`${API}/analytics/hourly`);
  mkChart("trend-chart", {
    type: "line",
    data: {
      labels: d.map(r => hh(r.hour)),
      datasets: [
        { label: "Actual volume", data: d.map(r => r.volume), borderColor: "#38bdf8", backgroundColor: "rgba(56,189,248,.15)", fill: true, tension: .35, yAxisID: "y" },
        { label: "Forecast volume", data: d.map(r => r.forecast), borderColor: "#f97316", borderDash: [6, 4], tension: .35, pointRadius: 0, yAxisID: "y" },
        { label: "Avg speed (km/h)", data: d.map(r => r.speed), borderColor: "#22c55e", tension: .35, pointRadius: 0, yAxisID: "y2" },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      scales: { x: axes.x, y: { ...axes.y, title: { display: true, text: "Vehicles / reading" } },
                y2: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "km/h" } } } },
  });
}

async function loadHeatmap() {
  const rows = await getJSON(`${API}/forecast/heatmap`);
  const now = new Date().getHours();
  let h = `<div></div>` + [...Array(24).keys()].map(i => `<div class="hh">${i}</div>`).join("");
  for (const r of rows) {
    h += `<div class="rl">${r.road_name}</div>`;
    for (let i = 0; i < 24; i++) {
      const c = r.cells.find(x => x.hour_of_day === i);
      const lvl = c ? c.congestion_level : "UNKNOWN";
      h += `<div class="cell${i === now ? " now" : ""}" style="background:${COL[lvl]}" title="${r.road_name} ${hh(i)}: ${lvl}${c ? " (" + c.predicted_volume + ")" : ""}"></div>`;
    }
  }
  $("heatmap").innerHTML = h;
}

async function loadRoads() {
  const rows = await getJSON(`${API}/roads/detail`);
  const tb = document.querySelector("#roads-table tbody");
  tb.innerHTML = rows.map(r => `<tr class="clickable" data-id="${r.road_id}" data-name="${r.road_name}">
    <td>${r.road_name}</td><td>${r.route}</td><td>${r.length_km} km</td><td>${r.lane_count}</td><td>${r.sensors}</td>
    <td>${r.avg_volume ?? "-"}</td><td>${r.avg_speed ?? "-"}</td><td>${r.peak_hour == null ? "-" : hh(r.peak_hour)}</td>
    <td><span class="badge ${r.current_level}">${r.current_level}</span></td></tr>`).join("");
  tb.querySelectorAll("tr").forEach(tr => tr.addEventListener("click", () => {
    tb.querySelectorAll("tr").forEach(x => x.classList.remove("sel"));
    tr.classList.add("sel");
    drillDown(tr.dataset.id, tr.dataset.name);
  }));
  if (rows.length && !charts["road-chart"]) { tb.firstElementChild.click(); }
}

async function drillDown(id, name) {
  const d = await getJSON(`${API}/forecast/road/${id}`);
  $("drill-title").textContent = `${name} — predicted volume by hour`;
  mkChart("road-chart", {
    type: "bar",
    data: { labels: d.map(r => hh(r.hour_of_day)),
            datasets: [{ data: d.map(r => r.predicted_volume), backgroundColor: d.map(r => COL[r.congestion_level]) }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: axes },
  });
}

async function loadAlerts() {
  const a = await getJSON(`${API}/alerts`);
  $("alerts-list").innerHTML = a.length
    ? a.map(x => `<li><span class="badge ${x.severity}">${x.severity}</span><span><strong>${x.road}</strong> — ${x.message}</span></li>`).join("")
    : `<li class="none">All roads flowing normally.</li>`;
}

async function loadSensorTypes() {
  const d = await getJSON(`${API}/sensors/types`);
  mkChart("sensor-chart", {
    type: "doughnut",
    data: { labels: d.map(r => r.sensor_type.replace("_", " ")), datasets: [{ data: d.map(r => r.n), backgroundColor: ["#38bdf8", "#a78bfa", "#f472b6"], borderColor: "#1e293b" }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
  });
}

async function loadRecent() {
  const d = await getJSON(`${API}/readings/recent?limit=15`);
  document.querySelector("#recent-table tbody").innerHTML = d.map(r =>
    `<tr><td>${r.ts}</td><td>${r.road_name}</td><td>#${r.sensor_id}</td><td>${r.sensor_type.replace("_", " ")}</td><td>${r.vehicle_count}</td><td>${r.avg_speed_kmh}</td></tr>`).join("");
}

function refreshExtras() {
  for (const [fn, label] of [[loadKpis, "kpis"], [loadTrend, "trend"], [loadHeatmap, "heatmap"], [loadRoads, "roads"],
                             [loadAlerts, "alerts"], [loadSensorTypes, "sensors"], [loadRecent, "recent"]]) {
    fn().catch(e => console.error("Failed to load " + label, e));
  }
}
window.refreshExtras = refreshExtras;

setInterval(() => { $("clock").textContent = new Date().toLocaleString(); }, 1000);
setInterval(() => { loadKpis().catch(() => {}); loadAlerts().catch(() => {}); loadRecent().catch(() => {}); }, 30000);
refreshExtras();
