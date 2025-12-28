#include <WiFiS3.h>
#include <ArduinoJson.h>
#include <DHT.h>

// Sensor pins
#define DHTPIN 8         // Digital pin connected to DHT11
#define DHTTYPE DHT11    // DHT 11

#define MQ2_PIN A0       // Analog pin connected to MQ-2 sensor

DHT dht(DHTPIN, DHTTYPE);

const char* ssid = "MagentaWLAN-NHL6";
const char* pass = "R.K.0106199018081994"; 

int status = WL_IDLE_STATUS;
char server[] = "khaledkassar.pythonanywhere.com"; 
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