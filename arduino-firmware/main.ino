#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#include <DHT.h>
#include <MPU9250_asukiaaa.h>

#define DHT_PIN 2
#define DHT_TYPE DHT22
#define SERIAL_BAUD 9600
#define SAMPLE_INTERVAL_MS 2000UL

const float STANDARD_GRAVITY = 9.80665f;
const char* DEVICE_UID = "SCX-IOT-001";
const char* PRODUCT_UNIT_ID = "1";

DHT dht(DHT_PIN, DHT_TYPE);
MPU9250_asukiaaa mpu;
unsigned long lastSampleAt = 0;

void printReading(float temperature, float humidity, float ax, float ay, float az) {
  float magnitude = sqrt((ax * ax) + (ay * ay) + (az * az));

  Serial.print("SCX|");
  Serial.print(DEVICE_UID);
  Serial.print("|");
  Serial.print(PRODUCT_UNIT_ID);
  Serial.print("|");
  Serial.print(temperature, 2);
  Serial.print("|");
  Serial.print(humidity, 2);
  Serial.print("|");
  Serial.print(ax, 2);
  Serial.print("|");
  Serial.print(ay, 2);
  Serial.print("|");
  Serial.print(az, 2);
  Serial.print("|");
  Serial.println(magnitude, 2);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  dht.begin();
  Wire.begin();
  mpu.setWire(&Wire);
  mpu.beginAccel();
  mpu.beginGyro();
  mpu.beginMag();
  delay(1000);
}

void loop() {
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  if (isnan(temperature)) temperature = 22.0f;
  if (isnan(humidity)) humidity = 45.0f;

  float ax = 0.0f;
  float ay = 0.0f;
  float az = STANDARD_GRAVITY;

  if (mpu.accelUpdate() == 0) {
    ax = mpu.accelX() * STANDARD_GRAVITY;
    ay = mpu.accelY() * STANDARD_GRAVITY;
    az = mpu.accelZ() * STANDARD_GRAVITY;
  }

  unsigned long now = millis();
  if (now - lastSampleAt >= SAMPLE_INTERVAL_MS || lastSampleAt == 0) {
    printReading(temperature, humidity, ax, ay, az);
    lastSampleAt = now;
  }

  delay(50);
}