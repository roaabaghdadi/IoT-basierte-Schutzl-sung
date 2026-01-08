
#  IoT-basierte-Schutzlösung
Ein einfaches, datenschutzfreundliches System zur Echtzeit-Überwachung von Temperatur, Luftfeuchte und gefährlichen Gasen.



## Test
Zur Test-URL navigieren:

Einen Webbrowser öffnen.

Die Test-URL (https://roaabaghdadi.pythonanywhere.com/login) in die Adressleiste eingeben und Enter drücken.

Anmeldedaten eingeben:

Das Feld E-Mail auf der Login-Seite finden.

Die registrierte Test-E-Mail-Adresse eingeben (admin@safety.com).

Das entsprechende gültige Passwort eingeben (secret123).

Sensorwerte werden angezeigt.


## 📦 Benötigte Hardware

| Komponente | Modell | Hinweis |
|-----------|--------|---------|
| Mikrocontroller | **Arduino Uno R4 WiFi** | Integrierter ESP32-C3 — kein externes WLAN-Modul nötig |
| Temperatur-/Luftfeuchte-Sensor | **DHT11** | Präziser als DHT11 (±0.3 °C, ±2 % r.F.), I²C-Schnittstelle |
| Gassensor | **MQ-2** | Erkennt entflammbare Gase, Rauch, CO-Äquivalent (analoger Ausgang) |
| Optional | LED, Piezo-Summer, OLED-Display | Für lokale optische/akustische Warnung direkt am Gerät |

---

## 🔌 Verkabelung (Arduino Uno R4 WiFi)

```
DHT11:
  VCC → 3.3V   (nicht 5V!)
  GND → GND
  SDA → Pin 18 (SDA)
  SCL → Pin 19 (SCL)
  ➕ Empfohlen: 4.7 kΩ Pull-up an SDA und SCL

MQ-2:
  VCC → 5V
  GND → GND
  A0  → A0 (analoger Eingang)

Aktoren (optional):
  LED+ → Digital Pin 2 (mit 220 Ω Vorwiderstand)
  Buzzer → Digital Pin 3
```

## 📦 Beispiel-Daten (JSON)

Der Arduino sendet folgendes Format an `POST /api/data`:

```json
{
  "temperature": 24.5,
  "humidity": 52.3,
  "gas_level": 480,
  "co_ppm": 140
}
```

> 📝 `co_ppm` ist ein Schätzwert (CO ≈ 30 % des Gesamtgaswerts). Für genaue CO-Messung ist ein **MQ-2** empfohlen.

---

## 📄 Arduino-Code (Auszug)

```cpp
#include <WiFiS3.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Sensor pins
#define DHTPIN 8         // Digital pin connected to DHT11
#define DHTTYPE DHT11    // DHT 11

#define MQ2_PIN A0       // Analog pin connected to MQ-2 sensor

DHT dht(DHTPIN, DHTTYPE);

const char* ssid = "your Netword SSID";
const char* pass = "Network Password";

int status = WL_IDLE_STATUS;
char server[] = "roaabaghdadi.pythonanywhere.com";
int port = 80;  // HTTP port

WiFiClient client;

// Variables for sensors
float temperature = 0.0;
float humidity = 0.0;
int gasValue = 0;
float gasVoltage = 0.0;
float coPPM = 0.0;

// MQ-2 calibration constants for CO detection
#define RL_VALUE 5.0     // Load resistance in kilo-ohms
#define RO_CLEAN_AIR 9.8 // Sensor resistance in clean air (may need calibration)
#define CO_A 605.18      // CO curve constant A
#define CO_B -3.937      // CO curve constant B

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // wait for serial port to connect
  }

  // Initialize sensors
  dht.begin();
  pinMode(MQ2_PIN, INPUT);

  connectToWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Attempting to reconnect...");
    connectToWiFi();
  } else {
    // Send data every 10 seconds
    sendDataToServer();
    delay(10000);
  }
}

void connectToWiFi() {
  Serial.println("Attempting to connect to SSID: ");
  Serial.println(ssid);

  status = WiFi.begin(ssid, pass);

  int attempts = 0;
  while (status != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    status = WiFi.status();
    attempts++;
  }

  if (status == WL_CONNECTED) {
    Serial.println("\nConnected to Wi-Fi!");
    printWifiStatus();
  } else {
    Serial.println("\nFailed to connect to WiFi!");
  }
}

float calculateCOppm(int rawADC) {
  // Convert analog reading to voltage
  float voltage = rawADC * (5.0 / 1024.0);

  // Calculate sensor resistance (RS)
  float RS = ((5.0 * RL_VALUE) / voltage) - RL_VALUE;

  // Calculate RS/RO ratio
  float ratio = RS / RO_CLEAN_AIR;

  // Calculate PPM using the power law equation for CO: PPM = A * (RS/RO)^B
  // Note: This is an approximation and requires proper calibration
  float ppm = CO_A * pow(ratio, CO_B);

  return ppm;
}

void readSensors() {
  // Read temperature and humidity from DHT11
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  // Read gas sensor from MQ-2
  gasValue = analogRead(MQ2_PIN);
  gasVoltage = (gasValue * 5.0) / 1024.0;  // For 5V systems

  // Calculate CO PPM (approximation)
  coPPM = calculateCOppm(gasValue);

  Serial.print("Gas Sensor Value: ");
  Serial.print(gasValue);
  Serial.print(" | Voltage: ");
  Serial.print(gasVoltage);
  Serial.print("V | CO PPM: ");
  Serial.print(coPPM);
  Serial.println(" ppm");
}

void sendDataToServer() {
  Serial.println("\nSending data to server...");

  // Read all sensor data before sending
  readSensors();

  if (client.connect(server, port)) {
    Serial.println("Connected to server");

    // Create JSON data with all sensors
    StaticJsonDocument<300> doc;  // Increased size for additional data

    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["gas_level"] = gasValue;        // Raw analog value (0-1023)
    doc["co_ppm"] = coPPM;              // Calculated CO PPM value

    String jsonData;
    serializeJson(doc, jsonData);

    // Send HTTP POST request
    client.println("POST /api/data HTTP/1.1");
    client.println("Host: " + String(server));
    client.println("Content-Type: application/json");
    client.println("Connection: close");
    client.print("Content-Length: ");
    client.println(jsonData.length());
    client.println();
    client.println(jsonData);

    Serial.println("Data sent: " + jsonData);

    // Wait for response
    unsigned long timeout = millis();
    while (client.connected() && millis() - timeout < 5000L) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        Serial.println(line);
      }
    }

    client.stop();
    Serial.println("Connection closed");

  } else {
    Serial.println("Connection to server failed!");
  }
}

void printWifiStatus() {
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  long rssi = WiFi.RSSI();
  Serial.print("Signal strength (RSSI): ");
  Serial.print(rssi);
  Serial.println(" dBm");
}



```

🔧 **Kalibrierung des MQ-2**:
Nutzen Sie das [MQ-2-Datenblatt](https://www.sparkfun.com/datasheets/Sensors/Biometric/MQ-2.pdf) für eine 2-Punkt-Kalibrierung (Nullpunkt + Testgas).

---

## 🖥️ Flask-Server (Backend)

- Läuft lokal (z. B. auf Raspberry Pi oder PC im Netzwerk)
- Web-Oberfläche zum Einrichten von Schwellenwerten und Alarmen
- Unterstützt:
  - ✉️ **E-Mail-Alarme** (über lokalen SMTP oder Gmail-App-Passwort)
  - 🌐 **Webhook-Alarme** (z. B. an `http://192.168.1.50/alarm`)

🔐 **Datenschutz**:
- Keine personenbezogenen Daten außer E-Mail für Alarme
- Kein Logging, keine Telemetrie, keine Cloud-Abhängigkeit
- Passwörter werden gehasht gespeichert (empfohlen)

---

## 📁 Projektstruktur

```
iot-safety/
├── app/
│   ├── routes.py        ← Hauptlogik (API, Alarme, Login)
│   └── models.py        ← Datenbankmodelle (User, SensorData, Alert)
├── templates/
│   ├── login.html
│   ├── index.html       ← Dashboard
│   └── settings.html    ← Schwellenwerte verwalten
├── arduino/
│   └── sketch_IoT.ino ← Arduino-Code
├── .env
├── requirements.txt
└── README.md            ← Diese Datei
```

---

## 🚀 Loslegen

1. Arduino-Code auf Uno R4 flashen
2. Flask-Server starten (`flask run --host=0.0.0.0`)
3. Im Browser anmelden → Schwellenwerte einstellen
4. Fertig! 🎉 System überwacht automatisch und warnt bei Gefahr.


