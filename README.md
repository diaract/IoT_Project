# 🌬️ Know The Air You Breathe In

**Know The Air You Breathe In** is a low-cost, modular, and distributed air quality monitoring system
designed to detect and visualize air pollution events in **industrial zones, educational spaces,
and indoor environments**.

The project aims to transform subjective air quality complaints into **objective, measurable,
and traceable data** by combining **IoT sensor nodes**, **wireless communication**, **backend-based
data processing**, and a **web-based visualization dashboard**.

---

## 🚀 System Architecture

The system is designed as a layered and scalable architecture:

### 🟢 Sensor Nodes (ESP32 / ESP8266)
Each sensor node collects environmental and air quality data:

- **SGP30**
  - TVOC (Total Volatile Organic Compounds) in **ppb**
  - eCO₂ (equivalent CO₂) in **ppm**
- **BME680**
  - Temperature
  - Humidity
  - Pressure
- **DHT11**
  - Temperature
  - Relative Humidity  
  *(used as a supporting sensor to provide environmental context and redundancy)*
- **LoRa RA-02 (SX1278)**
  - Long-range, low-power wireless data transmission

Sensor nodes periodically send measured data packets to the gateway.

---

### 🟡 Gateway
- Receives data from sensor nodes via **LoRa**
- Acts as a bridge between the LoRa network and the internet
- Forwards sensor data to the backend using **HTTP over Wi-Fi**
- Enables centralized data collection from multiple distributed nodes

---

### 🔵 Backend (FastAPI)
The backend acts as the **core intelligence layer** of the system:

- Receives sensor data via REST API (`/ingest`)
- Stores measurements in a **SQLite database**
- Provides data access endpoints:
  - Latest measurement
  - Historical time-series data
  - Alarm status
- Implements **relative-change–based alarm logic**:
  - Instead of fixed thresholds, pollution is detected by comparing current values
    against a **sliding baseline window**
  - This approach adapts to different environments and reduces false alarms
- Designed to be **TinyML-ready** for future anomaly detection models

---

### 🟣 Frontend Dashboard
- Web-based interface built with **HTML, CSS, and JavaScript**
- Connects directly to the backend REST API
- Displays:
  - Real-time air quality status (OK / WARN / HIGH)
  - Pollution score
  - TVOC and eCO₂ values
  - Historical charts for trend analysis
- Clearly visualizes pollution events with alert indicators
- Designed so that UI/UX can evolve independently from backend logic

---

## 🧪 Demo Scenario

A **transparent air tunnel / box** is used to demonstrate the system:

1. Clean air baseline is established
2. Smoke (match or cigarette) is introduced into the enclosure
3. TVOC and eCO₂ values increase sharply
4. Backend detects a significant relative change
5. Dashboard displays **“Air Pollution: HIGH!”** in real time

This setup provides a clear and intuitive demonstration suitable for
**classrooms, offices, and project presentations**.

---

## 📂 Project Structure

```text
firmware/   → ESP32 / ESP8266 sensor and gateway code
backend/    → FastAPI backend + SQLite database
frontend/   → Web dashboard (HTML / CSS / JS)
docs/       → Architecture diagrams, API docs, demo notes

---

## ⚙️ Technologies Used
- ESP32 / ESP8266
- SGP30, BME680, DHT11
- LoRa RA-02 (SX1278)
- FastAPI (Python)
- SQLite
- HTML / CSS / JavaScript
- Chart.js (for visualization)
- TinyML (planned)

---

## 📌 Future Work
- TinyML-based anomaly detection (LSTM)
- Emission source localization using multi-node   triangulation
- Multi-node large-scale deployment
- Edge-based alerts and local decision-making
- Integration of additional gas sensors (CO, real CO₂)
