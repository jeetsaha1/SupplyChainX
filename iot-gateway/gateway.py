"""Read Arduino telemetry or generate mock readings and post them to FastAPI."""

import math
import os
import random
import time
from datetime import datetime, timezone

import requests

try:
    import serial  # type: ignore[import-not-found]
except ImportError:
    serial = None


SERIAL_PORT = os.getenv("SCX_SERIAL_PORT", "COM3")
SERIAL_BAUD = int(os.getenv("SCX_SERIAL_BAUD", "9600"))
BACKEND_URL = os.getenv("SCX_BACKEND_URL", "http://localhost:8000/api/v1/iot/readings")
DEVICE_UID = os.getenv("SCX_DEVICE_UID", "ARDUINO-UNO-001")
PRODUCT_UNIT_ID = int(os.getenv("SCX_PRODUCT_UNIT_ID", "1"))
PRODUCT_UNIT_IDS = [
    int(value.strip())
    for value in os.getenv("SCX_PRODUCT_UNIT_IDS", "1,2,3,4,5,6").split(",")
    if value.strip()
]
INTERVAL_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = float(os.getenv("SCX_REQUEST_TIMEOUT", "5"))
RETRY_DELAY_SECONDS = float(os.getenv("SCX_RETRY_DELAY", "2"))
mock_cycle = 0


def mock_reading() -> dict[str, object]:
    global mock_cycle

    product_unit_id = PRODUCT_UNIT_IDS[mock_cycle % len(PRODUCT_UNIT_IDS)] if PRODUCT_UNIT_IDS else PRODUCT_UNIT_ID
    mock_cycle += 1
    accel_x = round(random.uniform(-0.2, 0.2), 3)
    accel_y = round(random.uniform(-0.2, 0.2), 3)
    accel_z = round(random.uniform(0.85, 1.05), 3)
    return {
        "device_uid": DEVICE_UID if DEVICE_UID != "ARDUINO-UNO-001" else f"SCX-IOT-{product_unit_id:03d}",
        "product_unit_id": product_unit_id,
        "temperature": round(random.uniform(18.0, 26.0), 2),
        "humidity": round(random.uniform(45.0, 70.0), 2),
        "accel_x": accel_x,
        "accel_y": accel_y,
        "accel_z": accel_z,
        "accel_magnitude": round(math.sqrt(accel_x**2 + accel_y**2 + accel_z**2), 3),
    }


def parse_serial_line(line: str) -> dict[str, object]:
    fields = line.strip().split("|")
    if len(fields) != 9 or fields[0] != "SCX":
        raise ValueError("Expected SCX serial format with exactly 9 fields")

    values = {
        "device_uid": fields[1],
        "product_unit_id": int(fields[2]),
        "temperature": float(fields[3]),
        "humidity": float(fields[4]),
        "accel_x": float(fields[5]),
        "accel_y": float(fields[6]),
        "accel_z": float(fields[7]),
        "accel_magnitude": float(fields[8]),
    }
    numeric_values = [values[key] for key in ("temperature", "humidity", "accel_x", "accel_y", "accel_z", "accel_magnitude")]
    if not all(math.isfinite(float(value)) for value in numeric_values):
        raise ValueError("Sensor values must be finite numbers")
    return values


def post_reading(reading: dict[str, object]) -> None:
    for attempt in range(1, 4):
        try:
            response = requests.post(BACKEND_URL, json=reading, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            print(f"Posted reading: {response.status_code}")
            return
        except requests.RequestException as error:
            if attempt == 3:
                print(f"Backend request failed after {attempt} attempts; reading dropped: {error}")
                return
            print(f"Backend request failed on attempt {attempt}; retrying: {error}")
            time.sleep(RETRY_DELAY_SECONDS)


def run() -> None:
    connection = None
    if serial is not None:
        try:
            connection = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
            print(f"Reading Arduino telemetry from {SERIAL_PORT}")
        except serial.SerialException:
            print(f"Serial port {SERIAL_PORT} unavailable; using mock mode")
    else:
        print("pyserial unavailable; using mock mode")

    try:
        while True:
            if connection is not None and connection.in_waiting:
                try:
                    reading = parse_serial_line(connection.readline().decode("utf-8"))
                except (UnicodeDecodeError, ValueError) as error:
                    print(f"Skipped serial line: {error}")
                    continue
            else:
                reading = mock_reading()
                print(f"Mock reading: {reading}")

            post_reading(reading)
            time.sleep(INTERVAL_SECONDS)
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    run()