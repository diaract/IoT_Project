import { CONFIG } from "./config.js";

const $ = (id) => document.getElementById(id);

// Global variables
let map;
let markers = [];
let circles = [];
let heatLayer = null;
let currentFilter = { city: "", district: "" };
let selectedLocation = null;
let chart;

// Layer visibility states
let showMarkers = true;
let showCircles = true;
let showHeatmap = false;

// Show API info
$("apiBase").textContent = CONFIG.API_BASE;

// API REQUESTS
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

// MAP FUNCTIONS
function initMap() {
  // Initialize Leaflet map
  map = L.map('map').setView(CONFIG.MAP_CENTER, CONFIG.MAP_ZOOM);
  
  // Add OpenStreetMap tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(map);
  
  // Setup control event listeners
  setupMapControls();
}

function setupMapControls() {
  $("showMarkers").addEventListener("change", (e) => {
    showMarkers = e.target.checked;
    updateLayerVisibility();
  });
  
  $("showCircles").addEventListener("change", (e) => {
    showCircles = e.target.checked;
    updateLayerVisibility();
  });
  
  $("showHeatmap").addEventListener("change", (e) => {
    showHeatmap = e.target.checked;
    updateLayerVisibility();
  });
}

function updateLayerVisibility() {
  // Show/hide markers
  markers.forEach(marker => {
    if (showMarkers) {
      marker.addTo(map);
    } else {
      map.removeLayer(marker);
    }
  });
  
  // Show/hide circles
  circles.forEach(circle => {
    if (showCircles) {
      circle.addTo(map);
    } else {
      map.removeLayer(circle);
    }
  });
  
  // Show/hide heat map
  if (heatLayer) {
    if (showHeatmap) {
      heatLayer.addTo(map);
    } else {
      map.removeLayer(heatLayer);
    }
  }
}

function getQualityColor(tvoc) {
  if (tvoc === null || tvoc === undefined) return CONFIG.COLORS.NO_DATA;
  if (tvoc <= CONFIG.THRESHOLDS.GOOD) return CONFIG.COLORS.GOOD;
  if (tvoc <= CONFIG.THRESHOLDS.MODERATE) return CONFIG.COLORS.MODERATE;
  return CONFIG.COLORS.POOR;
}

function getQualityText(tvoc) {
  if (tvoc === null || tvoc === undefined) return "NO DATA";
  if (tvoc <= CONFIG.THRESHOLDS.GOOD) return "GOOD";
  if (tvoc <= CONFIG.THRESHOLDS.MODERATE) return "MODERATE";
  return "POOR";
}

function getQualityClass(tvoc) {
  if (tvoc === null || tvoc === undefined) return "no-data";
  if (tvoc <= CONFIG.THRESHOLDS.GOOD) return "good";
  if (tvoc <= CONFIG.THRESHOLDS.MODERATE) return "moderate";
  return "poor";
}

function getHeatIntensity(tvoc) {
  // Heat map intensity value (0-1 range)
  if (tvoc === null || tvoc === undefined) return 0.1;
  if (tvoc <= CONFIG.THRESHOLDS.GOOD) return 0.3;
  if (tvoc <= CONFIG.THRESHOLDS.MODERATE) return 0.6;
  return 1.0;
}

function getCircleRadius(tvoc) {
  // Circle radius based on TVOC value (in meters)
  if (tvoc === null || tvoc === undefined) return 2000;
  if (tvoc <= CONFIG.THRESHOLDS.GOOD) return 3000;
  if (tvoc <= CONFIG.THRESHOLDS.MODERATE) return 4000;
  return 5000;
}

function createMarkerIcon(color) {
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background-color: ${color};
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 3px 10px rgba(0,0,0,0.4);
      position: relative;
    ">
      <div style="
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 8px solid transparent;
        border-right: 8px solid transparent;
        border-top: 8px solid ${color};
        filter: drop-shadow(0 2px 3px rgba(0,0,0,0.3));
      "></div>
    </div>`,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40],
  });
}

function addMarker(location) {
  const { lat, lon, name, tvoc_ppb, eco2_ppm, temperature, humidity, pressure, last_update } = location;
  
  const color = getQualityColor(tvoc_ppb);
  const quality = getQualityText(tvoc_ppb);
  
  // 1. Color Circle (Large Area)
  const circleRadius = getCircleRadius(tvoc_ppb);
  const circle = L.circle([lat, lon], {
    color: color,
    fillColor: color,
    fillOpacity: 0.2,
    radius: circleRadius,
    weight: 2
  });
  
  if (showCircles) {
    circle.addTo(map);
  }
  circles.push(circle);
  
  // 2. Marker (Point)
  const marker = L.marker([lat, lon], {
    icon: createMarkerIcon(color)
  });
  
  if (showMarkers) {
    marker.addTo(map);
  }

  // Popup content
  const popupContent = `
    <div class="popup-content">
      <h4>${name}</h4>
      <p><strong>TVOC:</strong> ${tvoc_ppb ?? "N/A"} ppb</p>
      <p><strong>eCO₂:</strong> ${eco2_ppm ?? "N/A"} ppm</p>
      <p><strong>Temperature:</strong> ${temperature ?? "N/A"}°C</p>
      <p><strong>Humidity:</strong> ${humidity ?? "N/A"}%</p>
      <div class="popup-quality" style="
        background: ${color};
        color: white;
      ">${quality}</div>
    </div>
  `;
  
  marker.bindPopup(popupContent);
  
  // Update detail panel when marker clicked
  marker.on('click', () => {
    showLocationDetail(location);
  });
  
  // Show details when circle clicked too
  circle.on('click', () => {
    showLocationDetail(location);
    marker.openPopup();
  });
  
  markers.push(marker);
}

function createHeatLayer(locations) {
  // Prepare data for heat map
  const heatData = locations
    .filter(loc => loc.tvoc_ppb !== null && loc.tvoc_ppb !== undefined)
    .map(loc => {
      const intensity = getHeatIntensity(loc.tvoc_ppb);
      return [loc.lat, loc.lon, intensity];
    });
  
  // Create heat layer
  if (heatLayer) {
    map.removeLayer(heatLayer);
  }
  
  heatLayer = L.heatLayer(heatData, {
    radius: 35,
    blur: 45,
    maxZoom: 13,
    max: 1.0,
    gradient: {
      0.0: CONFIG.COLORS.GOOD,
      0.5: CONFIG.COLORS.MODERATE,
      1.0: CONFIG.COLORS.POOR
    }
  });
  
  if (showHeatmap) {
    heatLayer.addTo(map);
  }
}

function clearMarkers() {
  markers.forEach(marker => map.removeLayer(marker));
  markers = [];
  
  circles.forEach(circle => map.removeLayer(circle));
  circles = [];
  
  if (heatLayer) {
    map.removeLayer(heatLayer);
    heatLayer = null;
  }
}

async function loadMapData() {
  try {
    // Get map data from API
    let endpoint = "/map/points";
    const params = [];
    
    if (currentFilter.city) params.push(`city=${encodeURIComponent(currentFilter.city)}`);
    if (currentFilter.district) params.push(`district=${encodeURIComponent(currentFilter.district)}`);
    
    if (params.length > 0) endpoint += "?" + params.join("&");
    
    const data = await apiGet(endpoint);
    
    clearMarkers();
    
    if (data.points && data.points.length > 0) {
      // Add markers and circles
      data.points.forEach(location => addMarker(location));
      
      // Create heat map layer
      createHeatLayer(data.points);
      
      // Focus on first point (if filtering)
      if (currentFilter.city || currentFilter.district) {
        const bounds = L.latLngBounds(data.points.map(p => [p.lat, p.lon]));
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    } else {
      alert("No data found for this region.");
    }
    
    updateLastUpdate();
  } catch (e) {
    console.error("Error loading map data:", e);
    $("raw").textContent = `Error: ${e.message}`;
  }
}

// CITY/DISTRICT FUNCTIONS
async function loadCities() {
  try {
    const data = await apiGet("/locations/cities");
    const citySelect = $("ilSelect");
    
    citySelect.innerHTML = '<option value="">All Turkey</option>';
    
    if (data.cities) {
      data.cities.forEach(city => {
        const option = document.createElement("option");
        option.value = city;
        option.textContent = city;
        citySelect.appendChild(option);
      });
    }
  } catch (e) {
    console.error("Error loading cities:", e);
  }
}

async function loadDistricts(city) {
  try {
    const districtSelect = $("ilceSelect");
    districtSelect.innerHTML = '<option value="">All Districts</option>';
    
    if (!city) {
      districtSelect.disabled = true;
      return;
    }
    
    const data = await apiGet(`/locations/districts?city=${encodeURIComponent(city)}`);
    
    if (data.districts && data.districts.length > 0) {
      data.districts.forEach(district => {
        const option = document.createElement("option");
        option.value = district;
        option.textContent = district;
        districtSelect.appendChild(option);
      });
      districtSelect.disabled = false;
    } else {
      districtSelect.disabled = true;
    }
  } catch (e) {
    console.error("Error loading districts:", e);
    $("ilceSelect").disabled = true;
  }
}

// DETAIL PANEL
function showLocationDetail(location) {
  selectedLocation = location;
  
  $("noSelection").style.display = "none";
  $("detailPanel").style.display = "block";
  
  $("locationName").textContent = location.name || "Unknown Location";
  
  const quality = getQualityText(location.tvoc_ppb);
  const qualityClass = getQualityClass(location.tvoc_ppb);
  const badge = $("qualityBadge");
  badge.textContent = quality;
  badge.className = `quality-badge ${qualityClass}`;
  
  $("detailScore").textContent = location.score ?? "-";
  $("detailTvoc").textContent = location.tvoc_ppb ? `${location.tvoc_ppb} ppb` : "-";
  $("detailEco2").textContent = location.eco2_ppm ? `${location.eco2_ppm} ppm` : "-";
  $("detailTemp").textContent = location.temperature ? `${location.temperature}°C` : "-";
  $("detailHumidity").textContent = location.humidity ? `${location.humidity}%` : "-";
  $("detailPressure").textContent = location.pressure ? `${location.pressure} hPa` : "-";
  
  const timestamp = location.last_update ? new Date(location.last_update).toLocaleString('en-US') : "-";
  $("detailTimestamp").textContent = timestamp;
  
  // Load chart data for selected location
  loadChartForLocation(location.device_id || location.id);
}

// CHART FUNCTIONS
function initChart() {
  const ctx = $("chart");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { 
          label: "TVOC (ppb)", 
          data: [],
          borderColor: '#667eea',
          backgroundColor: 'rgba(102, 126, 234, 0.1)',
          tension: 0.4
        },
        { 
          label: "eCO₂ (ppm)", 
          data: [],
          borderColor: '#764ba2',
          backgroundColor: 'rgba(118, 75, 162, 0.1)',
          tension: 0.4
        },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: false,
      interaction: {
        intersect: false,
        mode: 'index',
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          borderColor: '#667eea',
          borderWidth: 1,
        }
      },
      scales: {
        x: { 
          ticks: { 
            maxTicksLimit: 10,
            font: { size: 11 }
          },
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            font: { size: 11 }
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          }
        }
      }
    }
  });
}

async function loadChartForLocation(deviceId) {
  if (!deviceId) return;
  
  try {
    const device = encodeURIComponent(deviceId);
    const history = await apiGet(`/history?device_id=${device}&limit=120`);
    
    updateChart(history.items || []);
  } catch (e) {
    console.error("Error loading chart data:", e);
  }
}

function updateChart(items) {
  if (!items || items.length === 0) {
    chart.data.labels = [];
    chart.data.datasets[0].data = [];
    chart.data.datasets[1].data = [];
    chart.update();
    return;
  }
  
  const labels = items.map(x => {
    const date = new Date(x.ts || x.timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  });
  const tvoc = items.map(x => x.tvoc_ppb ?? null);
  const eco2 = items.map(x => x.eco2_ppm ?? null);

  chart.data.labels = labels;
  chart.data.datasets[0].data = tvoc;
  chart.data.datasets[1].data = eco2;
  chart.update();
}

// EVENT LISTENERS
$("ilSelect").addEventListener("change", (e) => {
  currentFilter.city = e.target.value;
  currentFilter.district = "";
  $("ilceSelect").value = "";
  
  if (currentFilter.city) {
    loadDistricts(currentFilter.city);
  } else {
    $("ilceSelect").disabled = true;
    $("ilceSelect").innerHTML = '<option value="">Select city first</option>';
  }
});

$("ilceSelect").addEventListener("change", (e) => {
  currentFilter.district = e.target.value;
});

$("filterBtn").addEventListener("click", () => {
  loadMapData();
});

$("refreshBtn").addEventListener("click", () => {
  if (selectedLocation) {
    loadChartForLocation(selectedLocation.device_id || selectedLocation.id);
  }
});

// HELPER FUNCTIONS
function updateLastUpdate() {
  $("lastUpdate").textContent = new Date().toLocaleTimeString('en-US');
}

// INITIALIZATION

async function init() {
  initMap();
  initChart();
  await loadCities();
  await loadMapData();
  
  // Auto refresh (every 5 seconds)
  setInterval(() => {
    if (selectedLocation) {
      // Update only selected location data
      loadChartForLocation(selectedLocation.device_id || selectedLocation.id);
    }
  }, CONFIG.POLL_MS);
}

// Start when page loads
init();