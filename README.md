🌬️ Know The Air You Breathe In

Know The Air You Breathe In is a low-cost, distributed air quality monitoring system
designed to detect air pollution events in industrial, educational, and indoor environments
using objective, real-time sensor data.

The system integrates IoT-based sensing, LoRa communication, backend-driven intelligence,
and a web-based dashboard to provide both instant alerts and historical air quality analysis.
Rather than relying solely on fixed thresholds, the system evaluates relative changes over time,
making it adaptive to different environments.

🚀 System Architecture
🔹 Sensor Nodes (ESP32 / ESP8266)

Each sensor node continuously measures environmental and air quality parameters:

SGP30

TVOC (Total Volatile Organic Compounds) — ppb

eCO₂ (equivalent CO₂) — ppm

DHT11

Temperature — °C

Humidity — %RH

BME680 (optional / complementary)

Temperature, Humidity, Pressure

Gas resistance (for advanced air quality interpretation)

LoRa RA-02 (SX1278)

Long-range, low-power wireless data transmission

📌 DHT11 is used as a contextual sensor to support air quality interpretation, as gas sensor readings
are affected by temperature and humidity.

🔹 Gateway

Receives sensor data packets via LoRa

Acts as a bridge between sensor nodes and the backend

Sends structured JSON data to the backend using Wi-Fi + HTTP

🔹 Backend (FastAPI)

The backend is the core decision-making layer of the system.

Stores all measurements in a local database (SQLite)

Exposes RESTful API endpoints:

/ingest → receive sensor data

/latest → latest measurement

/history → historical time-series data

/alerts/latest → current pollution status

Implements adaptive alarm logic:

Computes a baseline using recent measurements

Detects pollution based on percentage increase over time

Produces pollution states:

OK

WARN

HIGH

Designed to be TinyML-ready for future anomaly detection models

📌 This backend-centered approach ensures consistent decision logic across all devices and interfaces.

🔹 Frontend Dashboard (HTML + JavaScript)

Lightweight, framework-free web interface

Connects directly to backend REST APIs

Displays:

Real-time sensor values

Pollution status and score

Historical graphs

Automatically refreshes data at fixed intervals

Clearly highlights alarm states (e.g., “Air Pollution: HIGH!”)

📌 The frontend focuses on visualization only; all processing and decision logic is handled by the backend.

🧪 Demo Scenario

To demonstrate the system, a transparent air tunnel or box is used:

Clean air baseline is established

Smoke (match or cigarette) is introduced

TVOC and eCO₂ values increase rapidly

Backend detects a significant percentage rise

Dashboard displays a HIGH pollution alert in real time

This setup provides a clear, visual, and data-driven demonstration of air pollution detection.

📂 Project Structure
firmware/   → ESP32 / ESP8266 sensor & gateway code
backend/    → FastAPI backend + database + alert logic
frontend/   → HTML + JavaScript dashboard
docs/       → Architecture, API, and demo documentation

⚙️ Technologies Used

ESP32 / ESP8266

SGP30, DHT11, BME680

LoRa RA-02 (SX1278)

FastAPI (Python)

SQLite

HTML + JavaScript Web Dashboard

TinyML (planned)

📌 Future Work

TinyML-based anomaly detection (LSTM)

Emission source localization via multi-node triangulation

Multi-node and city-scale deployment

Edge-level alerting and offline intelligence

Improved sensor calibration and data fusion

“You cannot improve what you cannot measure.”

This project emphasizes that objective measurement is the first step toward healthier indoor and urban environments.