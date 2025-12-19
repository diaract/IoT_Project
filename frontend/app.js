import { CONFIG } from "./config.js";

const $ = (id) => document.getElementById(id);

$("deviceId").textContent = CONFIG.DEVICE_ID;
$("apiBase").textContent = CONFIG.API_BASE;

function headers() {
  const h = { "accept": "application/json" };
  if (CONFIG.API_KEY && CONFIG.API_KEY.trim().length > 0) {
    h["x-api-key"] = CONFIG.API_KEY.trim();
  }
  return h;
}

async function apiGet(path) {
  const url = `${CONFIG.API_BASE}${path}`;
  const res = await fetch(url, { headers: headers() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return await res.json();
}

function setBadge(status) {
  const el = $("statusBadge");
  el.textContent = status || "OK";
  el.classList.remove("ok", "warn", "high");
  const s = (status || "OK").toUpperCase();
  if (s === "HIGH") el.classList.add("high");
  else if (s === "WARN" || s === "WARNING") el.classList.add("warn");
  else el.classList.add("ok");
}

let chart;

function initChart() {
  const ctx = $("chart");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "TVOC (ppb)", data: [] },
        { label: "eCO2 (ppm)", data: [] },
      ]
    },
    options: {
      responsive: true,
      animation: false,
      scales: {
        x: { ticks: { maxTicksLimit: 8 } }
      }
    }
  });
}

function updateChart(items) {
  // items: [{ts, tvoc_ppb, eco2_ppm, ...}]
  const labels = items.map(x => new Date(x.ts).toLocaleTimeString());
  const tvoc = items.map(x => x.tvoc_ppb ?? null);
  const eco2 = items.map(x => x.eco2_ppm ?? null);

  chart.data.labels = labels;
  chart.data.datasets[0].data = tvoc;
  chart.data.datasets[1].data = eco2;
  chart.update();
}

async function refresh() {
  try {
    const device = encodeURIComponent(CONFIG.DEVICE_ID);

    // 1) Alarm durumunu al (en net)
    const alert = await apiGet(`/alerts/latest?device_id=${device}`);

    $("lastUpdate").textContent = new Date().toLocaleTimeString();
    $("raw").textContent = JSON.stringify(alert, null, 2);

    $("score").textContent = alert.score ?? "-";
    $("tvoc").textContent = alert.tvoc_ppb ?? "-";
    $("eco2").textContent = alert.eco2_ppm ?? "-";
    setBadge(alert.status);

    // 2) History al (grafik için)
    const history = await apiGet(`/history?device_id=${device}&limit=120`);
    updateChart(history.items || []);
  } catch (e) {
    $("raw").textContent = `Error: ${e.message}`;
  }
}

$("refreshBtn").addEventListener("click", refresh);

initChart();
refresh();
setInterval(refresh, CONFIG.POLL_MS);
