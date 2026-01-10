#include <Arduino.h>
#include <Wire.h>
#include <math.h>

#include <DHT.h>
#include <Adafruit_BME680.h>
#include <Adafruit_SGP30.h>

#include <RadioLib.h>
#include <ArduinoJson.h>

// ==================== CONFIG ====================
#ifndef NODE_ID
#define NODE_ID "node-8"
#endif

#ifndef SAMPLE_PERIOD_MS
#define SAMPLE_PERIOD_MS 10000
#endif

#ifndef SAMPLE_PERIOD_ALERT_MS
#define SAMPLE_PERIOD_ALERT_MS 2000
#endif

#ifndef ALERT_HOLD_CYCLES
#define ALERT_HOLD_CYCLES 30
#endif

// ===== STATUS OUTPUTS =====
#define LED_GREEN  32
#define LED_RED    33
#define BUZZER_PIN 25

// ===== DELTA THRESHOLDS (ANİ DEĞİŞİM EŞİKLERİ) =====
#define ECO2_DELTA_PPM     30    // ppm
#define TVOC_DELTA_PPB     15    // ppb
#define TEMP_DELTA_C       0.5   // °C
#define HUM_DELTA_RH       2.0   // %
#define PRESS_DELTA_HPA    1.0   // hPa

// I2C (ESP32 default)
static const int I2C_SDA = 21;
static const int I2C_SCL = 22;

// DHT11
static const int DHT_PIN = 4;
static const int DHT_TYPE = DHT11;
DHT dht(DHT_PIN, DHT_TYPE);

// LoRa pins (ESP32 VSPI)
static const int LORA_SCK  = 18;
static const int LORA_MISO = 19;
static const int LORA_MOSI = 23;
static const int LORA_CS   = 27;    // NSS
static const int LORA_RST  = 14;    // RST
static const int LORA_DIO0 = 26;    // DIO0 (IRQ)

// Frequency
static const float LORA_FREQ_MHZ = 433.0;
// ================================================

// Sensors
Adafruit_BME680 bme;
Adafruit_SGP30 sgp;

// LoRa
SPIClass spiLoRa(VSPI);
SX1278 lora = new Module(LORA_CS, LORA_DIO0, LORA_RST, -1, spiLoRa);

uint32_t frameCounter = 0;

// ✅ LoRa hazır mı?
static bool loraReady = false;

// ✅ Buzzer latch (sürekli beep olmasın)
static bool buzzerLatched = false;

// ===== ÖNCEKİ DEĞERLER (DELTA DETECTION) =====
static int   prevEco2 = -1;
static int   prevTvoc = -1;
static float prevTemp = NAN;
static float prevHum  = NAN;
static float prevPres = NAN;

static void printReadings(float t, float h, float bp,
                          uint16_t eco2, uint16_t tvoc,
                          int score,
                          float predEco2_60m, float predTvoc_60m,
                          bool anEco2, bool anTvoc,
                          bool deltaAlert,
                          const String& status,
                          uint32_t sampleMs,
                          uint32_t fc) {
  Serial.println("\n================ SENSOR READINGS ================");

  Serial.print("BME680  | Temp: ");
  if (isnan(t)) Serial.print("N/A"); else Serial.print(t, 2);
  Serial.print(" °C  | Hum: ");
  if (isnan(h)) Serial.print("N/A"); else Serial.print(h, 1);
  Serial.print(" %  | Pressure: ");
  if (isnan(bp)) Serial.print("N/A"); else Serial.print(bp, 1);
  Serial.println(" hPa");

  Serial.print("SGP30   | eCO2: ");
  Serial.print(eco2);
  Serial.print(" ppm  | TVOC: ");
  Serial.print(tvoc);
  Serial.println(" ppb");

  Serial.print("TinyML  | score=");
  Serial.print(score);
  Serial.print(" | predEco2_60m=");
  Serial.print(predEco2_60m, 0);
  Serial.print(" ppm | predTvoc_60m=");
  Serial.print(predTvoc_60m, 0);
  Serial.println(" ppb");

  Serial.print("ANOMALY | eCO2_anom=");
  Serial.print(anEco2 ? "YES" : "NO");
  Serial.print(" | TVOC_anom=");
  Serial.println(anTvoc ? "YES" : "NO");

  Serial.print("DELTA   | deltaAlert=");
  Serial.print(deltaAlert ? "YES" : "NO");
  Serial.print(" | status=");
  Serial.print(status);
  Serial.print(" | sampleMs=");
  Serial.print(sampleMs);
  Serial.print(" | fc=");
  Serial.println(fc);

  Serial.println("=================================================\n");
}

// ================= TinyML-lite (RESPONSIVE) ===================
struct HoltForecast {
  float level = NAN;
  float trend = 0.0f;
  bool init = false;
  int updateCount = 0;

  // ⭐ AGGRESSIVE: Faster learning
  float alpha = 0.5f;   // Increased from 0.25 → more responsive to changes
  float beta  = 0.2f;   // Increased from 0.08 → trend adapts faster

  void update(float x) {
    if (!init) {
      level = x;
      trend = 0.0f;
      init = true;
      updateCount = 1;
      return;
    }
    
    float prevLevel = level;
    level = alpha * x + (1.0f - alpha) * (level + trend);
    trend = beta * (level - prevLevel) + (1.0f - beta) * trend;
    updateCount++;
  }

  float predict(int k) const {
    if (!init) return NAN;
    return level + (float)k * trend;
  }
  
  // ⭐ CLAMP prediction to realistic range
  float predictClamped(int k, float minVal, float maxVal) const {
    float pred = predict(k);
    if (isnan(pred)) return NAN;
    if (pred < minVal) return minVal;
    if (pred > maxVal) return maxVal;
    return pred;
  }
  
  // ⭐ Is model stable? (at least 5 updates)
  bool isStable() const {
    return init && (updateCount >= 5);
  }
};

struct AnomalyDetector {
  float emaErr2 = 0.0f;
  bool init = false;
  int updateCount = 0;

  // ⭐ AGGRESSIVE: Lower threshold
  float gamma = 0.15f;  // Increased from 0.05 → faster EMA update
  float mult = 4.0f;    // Decreased from 9.0 (3-sigma) → 2-sigma (more sensitive)

  bool update(float error) {
    float e2 = error * error;
    
    if (!init) {
      emaErr2 = e2;
      init = true;
      updateCount = 1;
      return false;  // Don't trigger on first update
    }
    
    emaErr2 = gamma * e2 + (1.0f - gamma) * emaErr2;
    updateCount++;
    
    // ⭐ Only trigger after model is stable (3+ updates)
    if (updateCount < 3) return false;
    
    float baseline = (emaErr2 < 1e-6f) ? 1e-6f : emaErr2;
    return (e2 > mult * baseline);
  }
  
  // ⭐ Reset if too many false positives
  void reset() {
    emaErr2 = 0.0f;
    init = false;
    updateCount = 0;
  }
};

HoltForecast holtEco2, holtTvoc;
AnomalyDetector anomEco2, anomTvoc;

static float oneStepErr(const HoltForecast& m, float current) {
  float p1 = m.predict(1);
  if (isnan(p1)) return 0.0f;
  return current - p1;
}
// ================================================

// ============== Air Quality Score ===============
static int clampInt(int v, int lo, int hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static int airScore(uint16_t eco2ppm, uint16_t tvocppb) {
  int sEco2;
  if (eco2ppm <= 450) sEco2 = 100;
  else if (eco2ppm >= 2000) sEco2 = 0;
  else {
    float t = (eco2ppm - 450.0f) / (2000.0f - 450.0f);
    sEco2 = (int)(100.0f * (1.0f - t));
  }

  int sTvoc;
  if (tvocppb <= 100) sTvoc = 100;
  else if (tvocppb >= 1000) sTvoc = 0;
  else {
    float t = (tvocppb - 100.0f) / (1000.0f - 100.0f);
    sTvoc = (int)(100.0f * (1.0f - t));
  }

  int score = (int)(0.6f * sEco2 + 0.4f * sTvoc);
  return clampInt(score, 0, 100);
}
// ================================================

bool initBME680() {
  if (!bme.begin(0x76)) {
    Serial.println("[BME680] 0x76 yok, 0x77 deniyorum...");
    if (!bme.begin(0x77)) {
      Serial.println("[BME680] Bulunamadı.");
      return false;
    }
  }
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);
  Serial.println("[BME680] OK");
  return true;
}

bool initSGP30() {
  if (!sgp.begin()) {
    Serial.println("[SGP30] Bulunamadı.");
    return false;
  }
  Serial.println("[SGP30] OK");
  return true;
}

static void applyLoRaParams() {
  lora.setSpreadingFactor(7);
  lora.setBandwidth(125.0);     // 125 kHz
  lora.setCodingRate(5);        // 4/5
  lora.setOutputPower(17);      // dBm
  lora.setPreambleLength(8);
  lora.setCRC(true);
  lora.setSyncWord(0x34);
}

bool initLoRa() {

  spiLoRa.begin(LORA_SCK, LORA_MISO, LORA_MOSI, -1);

  Serial.printf("[LoRa] Pins SCK=%d MISO=%d MOSI=%d CS=%d RST=%d DIO0=%d\n",
                LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS, LORA_RST, LORA_DIO0);
  Serial.printf("[LoRa] Freq=%.1f MHz\n", LORA_FREQ_MHZ);

  pinMode(LORA_RST, OUTPUT);
  digitalWrite(LORA_RST, LOW);
  delay(20);
  digitalWrite(LORA_RST, HIGH);
  delay(20);

  Serial.print("[LoRa] Init try #1... ");
  int state = lora.begin(LORA_FREQ_MHZ);
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("OK");
    applyLoRaParams();
    return true;
  }
  Serial.print("FAIL code=");
  Serial.println(state);

  digitalWrite(LORA_RST, LOW);
  delay(50);
  digitalWrite(LORA_RST, HIGH);
  delay(100);

  Serial.print("[LoRa] Init try #2... ");
  state = lora.begin(LORA_FREQ_MHZ);
  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("OK");
    applyLoRaParams();
    return true;
  }
  Serial.print("FAIL code=");
  Serial.println(state);

  return false;
}

// ✅ SHORT JSON PAYLOAD - LoRa için kompakt (~160 byte)
String buildPayloadJsonShort(float tempC, float humRH, float pressureHpa,
                             uint16_t tvocppb, uint16_t eco2ppm,
                             int score,
                             float predEco2_60m, float predTvoc_60m,
                             bool anEco2, bool anTvoc,
                             bool deltaAlert, const String& status,
                             uint32_t sampleMs,
                             uint32_t fc) {
  StaticJsonDocument<256> doc;

  doc["id"] = NODE_ID;
  doc["ts"] = (uint32_t)millis();
  doc["fc"] = fc;

  // Sensor readings (SHORT + scaled integers)
  if (!isnan(tempC))       doc["t"]  = (int)(tempC * 10);
  if (!isnan(humRH))       doc["h"]  = (int)(humRH * 10);
  if (!isnan(pressureHpa)) doc["p"]  = (int)pressureHpa;

  doc["e"] = eco2ppm;
  doc["v"] = tvocppb;

  doc["s"]  = score;
  doc["pe"] = (int)lroundf(predEco2_60m);
  doc["pv"] = (int)lroundf(predTvoc_60m);

  doc["ae"] = anEco2;
  doc["av"] = anTvoc;
  doc["da"] = deltaAlert;
  doc["st"] = status;
  doc["sm"] = sampleMs;

  String json;
  serializeJson(doc, json);
  return json;
}

// ---------- Adaptive sampling state ----------
static uint32_t currentSampleMs = SAMPLE_PERIOD_MS;
static int alertHold = 0;
// ---------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(300);

  Wire.begin(I2C_SDA, I2C_SCL);

  bool okBME = initBME680();
  bool okSGP = initSGP30();
  bool okLoRa = initLoRa();

  loraReady = okLoRa;

  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // Başlangıç durumu: her şey normal
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_RED, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  if (!okLoRa) Serial.println("⚠️ LoRa init failed");
  if (!okBME)  Serial.println("⚠️ BME680 yok (devam)");
  if (!okSGP)  Serial.println("⚠️ SGP30 yok (devam)");

  Serial.println("✅ ESP32 Sensor Node started");
  Serial.println("   - TinyML: AGGRESSIVE mode (alpha=0.5, beta=0.2)");
  Serial.println("   - Anomaly: 2-sigma threshold (mult=4.0)");
  Serial.println("   - Delta: Sudden change detection\n");
}

void loop() {
  frameCounter++;

  // -------- BME680 (temp + humidity + pressure) --------
  float t  = NAN;
  float h  = NAN;
  float bp = NAN;

  if (bme.performReading()) {
    t  = bme.temperature;
    h  = bme.humidity;
    bp = bme.pressure / 100.0f;
  } else {
    Serial.println("[BME680] performReading failed.");
  }

  // -------- SGP30 (eco2/tvoc) --------
  uint16_t eco2 = 0, tvoc = 0;
  if (sgp.IAQmeasure()) {
    eco2 = sgp.eCO2;
    tvoc = sgp.TVOC;
  } else {
    Serial.println("[SGP30] IAQmeasure failed.");
  }

  // ===== DELTA-BASED CHANGE DETECTION =====
  bool deltaAlert = false;

  if (prevEco2 >= 0) {
    if (abs((int)eco2 - prevEco2) >= ECO2_DELTA_PPM) {
      deltaAlert = true;
      Serial.println("🔴 DELTA: eCO2 changed!");
    }
  }
  if (prevTvoc >= 0) {
    if (abs((int)tvoc - prevTvoc) >= TVOC_DELTA_PPB) {
      deltaAlert = true;
      Serial.println("🔴 DELTA: TVOC changed!");
    }
  }
  if (!isnan(prevTemp) && !isnan(t)) {
    if (fabs(t - prevTemp) >= TEMP_DELTA_C) {
      deltaAlert = true;
      Serial.println("🔴 DELTA: Temperature changed!");
    }
  }
  if (!isnan(prevHum) && !isnan(h)) {
    if (fabs(h - prevHum) >= HUM_DELTA_RH) {
      deltaAlert = true;
      Serial.println("🔴 DELTA: Humidity changed!");
    }
  }
  if (!isnan(prevPres) && !isnan(bp)) {
    if (fabs(bp - prevPres) >= PRESS_DELTA_HPA) {
      deltaAlert = true;
      Serial.println("🔴 DELTA: Pressure changed!");
    }
  }

  // Şu anki değerleri sakla
  prevEco2 = eco2;
  prevTvoc = tvoc;
  prevTemp = t;
  prevHum  = h;
  prevPres = bp;

  // ===== TinyML: PREDICTION + ANOMALY =====
  holtEco2.update((float)eco2);
  holtTvoc.update((float)tvoc);

  // ⭐ FIXED: Always predict 60 minutes ahead
  const int k60 = 360;
  
  // ⭐ CLAMP predictions to realistic ranges
  float predEco2_60m = holtEco2.predictClamped(k60, 300.0f, 1600.0f);
  float predTvoc_60m = holtTvoc.predictClamped(k60, 0.0f, 1000.0f);

  // ⭐ Anomaly detection (only if model is stable)
  bool anEco2 = false;
  bool anTvoc = false;
  
  if (holtEco2.isStable()) {
    anEco2 = anomEco2.update(oneStepErr(holtEco2, (float)eco2));
    if (anEco2) {
      Serial.println("🟡 ANOMALY: eCO2 trend break detected!");
    }
  }
  
  if (holtTvoc.isStable()) {
    anTvoc = anomTvoc.update(oneStepErr(holtTvoc, (float)tvoc));
    if (anTvoc) {
      Serial.println("🟡 ANOMALY: TVOC trend break detected!");
    }
  }

  // ===== STATUS DECISION (DELTA VE ANOMALY) =====
  String status = (deltaAlert || anEco2 || anTvoc) ? "HIGH" : "NORMAL";

  // ===== LED & BUZZER (DELTA VE ANOMALY) =====
  if (deltaAlert || anEco2 || anTvoc) {
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_RED, HIGH);

    if (!buzzerLatched) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(200);
      digitalWrite(BUZZER_PIN, LOW);
      buzzerLatched = true;
    }
  } else {
    digitalWrite(LED_GREEN, HIGH);
    digitalWrite(LED_RED, LOW);
    digitalWrite(BUZZER_PIN, LOW);
    buzzerLatched = false;
  }

  int score = airScore(eco2, tvoc);

  // ===== ADAPTIVE SAMPLING (DELTA VE ANOMALY) =====
  if (deltaAlert || anEco2 || anTvoc) {
    alertHold = ALERT_HOLD_CYCLES;
    currentSampleMs = SAMPLE_PERIOD_ALERT_MS;
  } else {
    if (alertHold > 0) {
      alertHold--;
      currentSampleMs = SAMPLE_PERIOD_ALERT_MS;
    } else {
      currentSampleMs = SAMPLE_PERIOD_MS;
    }
  }

  // Print readings
  printReadings(t, h, bp,
                eco2, tvoc,
                score,
                predEco2_60m, predTvoc_60m,
                anEco2, anTvoc,
                deltaAlert,
                status,
                currentSampleMs,
                frameCounter);

  // ===== LORA TRANSMISSION (SHORT JSON) =====
  String payload = buildPayloadJsonShort(t, h, bp, tvoc, eco2,
                                         score,
                                         predEco2_60m, predTvoc_60m,
                                         anEco2, anTvoc,
                                         deltaAlert, status,
                                         currentSampleMs,
                                         frameCounter);

  Serial.print("[PAYLOAD_LEN] ");
  Serial.println(payload.length());

  Serial.print("[PAYLOAD] ");
  Serial.println(payload);

  if (loraReady) {
    const int MAX_LORA_LEN = 255;
    if (payload.length() > MAX_LORA_LEN) {
      Serial.println("⚠️ Payload too long -> SKIP TX");
      delay(currentSampleMs);
      return;
    }

    int state = lora.transmit(payload);
    if (state == RADIOLIB_ERR_NONE) {
      Serial.println("✅ [LoRa] TX SUCCESS\n");
    } else {
      Serial.print("❌ [LoRa] TX FAIL code=");
      Serial.println(state);
    }
  } else {
    Serial.println("⚠️ [LoRa] SKIP TX\n");
  }

  delay(currentSampleMs);
}