// frontend/config.js
export const CONFIG = {
  API_BASE: "http://127.0.0.1:8000",
  DEVICE_ID: "node-001",
  POLL_MS: 5000, // 5s - slightly longer interval for map
  API_KEY: "",
  
  // Map settings
  MAP_CENTER: [38.7312, 35.4787], // Kayseri coordinates (default)
  MAP_ZOOM: 7,
  
  // Air quality color codes
  COLORS: {
    GOOD: "#4CAF50",      // Green
    MODERATE: "#FF9800",   // Orange
    POOR: "#F44336",       // Red
    NO_DATA: "#9E9E9E"     // Gray
  },
  
  // Air quality threshold values (based on TVOC ppb)
  THRESHOLDS: {
    GOOD: 220,      // 0-220: Good
    MODERATE: 660   // 220-660: Moderate, 660+: Poor
  }
};