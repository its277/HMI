#include <OneWire.h>
#include <DallasTemperature.h>

// Change this to whatever GPIO pin the 'S' (Signal) pin is connected to
const int ONE_WIRE_BUS = 4; 

// Setup the OneWire and DallasTemperature libraries
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

void setup() {
  Serial.begin(115200);
  Serial.println("Starting DS18B20 Sensor Test...");
  
  // Initialize the sensor
  sensors.begin();
  
  // Optional: Check how many sensors are detected on the data line
  int deviceCount = sensors.getDeviceCount();
  Serial.print("Sensors found: ");
  Serial.println(deviceCount);
}

void loop() {
  Serial.print("Requesting temperature... ");
  sensors.requestTemperatures(); 
  
  // Get the temperature in Celsius
  float tempC = sensors.getTempCByIndex(0);

  // The library returns -127.0 if it cannot communicate with the sensor
  if (tempC == -127.0) {
    Serial.println("FAILED! Reading is -127.0 °C (Check wiring or broken sensor)");
  } else {
    Serial.print("SUCCESS! Temp: ");
    Serial.print(tempC);
    Serial.println(" °C");
  }

  // Wait 2 seconds before checking again
  delay(2000);
}