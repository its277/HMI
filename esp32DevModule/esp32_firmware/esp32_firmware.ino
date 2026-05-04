#include <WiFi.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------
// PIN DEFINITIONS
// ---------------------------------------------------------
#define ONE_WIRE_BUS 4    // DS18B20 Data pin
#define HEATER_PIN   18   // MOSFET Gate pin for Polyimide Heater
#define SERVO_PIN    19   // SG90 Servo PWM pin

// ---------------------------------------------------------
// WI-FI SoftAP SETTINGS
// ---------------------------------------------------------
const char* ssid = "YakSperm_Analyzer_AP";
const char* password = "yakpassword"; 

// ---------------------------------------------------------
// GLOBALS & STATE
// ---------------------------------------------------------
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
Servo myServo;

float targetTemp = 0.0;
float currentTemp = 0.0;

unsigned long lastTempRequest = 0;
unsigned long lastStatusUpdate = 0;
const unsigned long TEMP_READ_INTERVAL = 500;   // ms
const unsigned long STATUS_TX_INTERVAL = 1000;  // ms

// PID Variables
float kp = 40.0;
float ki = 2.0;
float kd = 10.0;
float integral = 0.0;
float previousError = 0.0;
unsigned long lastPidTime = 0;
const int PWM_CHANNEL = 0;
const int PWM_FREQ = 1000;
const int PWM_RES = 8;

// ---------------------------------------------------------
// SETUP
// ---------------------------------------------------------
void setup() {
  Serial.begin(115200);
  
  // 1. Initialize Heater with LEDC PWM
  ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RES);
  ledcAttachPin(HEATER_PIN, PWM_CHANNEL);
  ledcWrite(PWM_CHANNEL, 0); // Ensure off at boot
  
  // 2. Initialize Wi-Fi Access Point
  WiFi.softAP(ssid, password);
  
  // 3. Initialize DS18B20 Temperature Sensor
  sensors.begin();
  sensors.setWaitForConversion(false); // Async temp reading
  sensors.requestTemperatures();
  
  // 4. Initialize Servo
  myServo.attach(SERVO_PIN);
  myServo.write(0); // Initial retracted position
}

// ---------------------------------------------------------
// MAIN LOOP
// ---------------------------------------------------------
void loop() {
  handleSerial();
  handleTemperature();
  handleHeater();
}

// ---------------------------------------------------------
// SERIAL PROTOCOL PARSER
// ---------------------------------------------------------
void handleSerial() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    
    // Support ArduinoJson v6 and v7
    #if ARDUINOJSON_VERSION_MAJOR >= 7
      JsonDocument doc;
    #else
      StaticJsonDocument<256> doc;
    #endif
    
    DeserializationError error = deserializeJson(doc, line);
    if (!error) {
      const char* cmd = doc["cmd"];
      if (cmd) {
        if (strcmp(cmd, "set_temp") == 0) {
          targetTemp = doc["value"];
          // Reset PID state when new temp is set
          integral = 0.0;
          previousError = 0.0;
          sendAck("set_temp");
          
        } else if (strcmp(cmd, "heater_off") == 0) {
          targetTemp = 0;
          ledcWrite(PWM_CHANNEL, 0);
          sendAck("heater_off");
          
        } else if (strcmp(cmd, "servo_move") == 0) {
          int pos = doc["position"];
          myServo.write(pos);
          sendAck("servo_move");
          
        } else if (strcmp(cmd, "ping") == 0) {
          #if ARDUINOJSON_VERSION_MAJOR >= 7
            JsonDocument reply;
          #else
            StaticJsonDocument<64> reply;
          #endif
          reply["type"] = "pong";
          serializeJson(reply, Serial);
          Serial.println();
        }
      }
    }
  }
}

// ---------------------------------------------------------
// TEMPERATURE READING & STATUS BROADCAST
// ---------------------------------------------------------
void handleTemperature() {
  unsigned long now = millis();
  
  // Read Temperature Asynchronously
  if (now - lastTempRequest >= TEMP_READ_INTERVAL) {
    float tempC = sensors.getTempCByIndex(0);
    if (tempC != DEVICE_DISCONNECTED_C) {
      currentTemp = tempC;
    }
    sensors.requestTemperatures(); // Start next conversion
    lastTempRequest = now;
  }
  
  // Send Status JSON periodically
  if (now - lastStatusUpdate >= STATUS_TX_INTERVAL) {
    #if ARDUINOJSON_VERSION_MAJOR >= 7
      JsonDocument doc;
    #else
      StaticJsonDocument<64> doc;
    #endif
    
    doc["type"] = "status";
    doc["temp"] = currentTemp;
    serializeJson(doc, Serial);
    Serial.println();
    
    lastStatusUpdate = now;
  }
}

// ---------------------------------------------------------
// HEATER CONTROL (PWM-based PID)
// ---------------------------------------------------------
void handleHeater() {
  if (targetTemp <= 0) {
    ledcWrite(PWM_CHANNEL, 0);
    return;
  }

  // Safety cutoff: if temp exceeds 50C, disable heater
  if (currentTemp >= 50.0) {
    ledcWrite(PWM_CHANNEL, 0);
    return;
  }

  unsigned long now = millis();
  float dt = (now - lastPidTime) / 1000.0; // Time delta in seconds

  if (dt >= 0.1) { // Run PID loop at 10Hz
    float error = targetTemp - currentTemp;
    
    // Proportional
    float pOut = kp * error;
    
    // Integral with anti-windup (only integrate if error is small)
    if (abs(error) < 5.0) {
      integral += error * dt;
    } else {
      integral = 0.0;
    }
    float iOut = ki * integral;
    
    // Derivative
    float derivative = (error - previousError) / dt;
    float dOut = kd * derivative;
    
    // Compute total output
    float output = pOut + iOut + dOut;
    
    // Clamp PWM to 0-255
    int pwmValue = 0;
    if (output > 255.0) pwmValue = 255;
    else if (output > 0.0) pwmValue = (int)output;
    
    ledcWrite(PWM_CHANNEL, pwmValue);
    
    previousError = error;
    lastPidTime = now;
  }
}

// ---------------------------------------------------------
// HELPERS
// ---------------------------------------------------------
void sendAck(const char* cmd) {
  #if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
  #else
    StaticJsonDocument<64> doc;
  #endif
  
  doc["type"] = "ack";
  doc["cmd"] = cmd;
  serializeJson(doc, Serial);
  Serial.println();
}
