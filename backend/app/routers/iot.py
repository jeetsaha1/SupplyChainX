from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tables import DeviceStatus, IotDevice, IotReading, ProductUnit, ProvenanceFlag
from app.schemas.iot import IoTDeviceCreate, IoTReadingCreate
from app.services.ai_service import score_iot_reading


router = APIRouter()


def device_payload(device: IotDevice) -> dict[str, Any]:
    return {
        "id": device.id,
        "device_uid": device.device_uid,
        "product_unit_id": device.product_unit_id,
        "device_status": device.device_status.value,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "created_at": device.created_at.isoformat(),
    }


def reading_payload(reading: IotReading) -> dict[str, Any]:
    return {
        "id": reading.id,
        "device_id": reading.device_id,
        "product_unit_id": reading.product_unit_id,
        "timestamp": reading.timestamp.isoformat(),
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "accel_x": reading.accel_x,
        "accel_y": reading.accel_y,
        "accel_z": reading.accel_z,
        "accel_magnitude": reading.accel_magnitude,
        "created_at": reading.created_at.isoformat(),
    }


@router.post("/devices", status_code=status.HTTP_201_CREATED)
def register_device(payload: IoTDeviceCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    product_unit = db.get(ProductUnit, payload.product_unit_id)
    if product_unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")

    device = db.scalar(select(IotDevice).where(IotDevice.device_uid == payload.device_uid))
    if device is None:
        device = IotDevice(
            device_uid=payload.device_uid,
            product_unit_id=payload.product_unit_id,
            device_status=DeviceStatus.ACTIVE,
        )
        db.add(device)
    else:
        device.product_unit_id = payload.product_unit_id
        device.device_status = DeviceStatus.ACTIVE
    db.commit()
    db.refresh(device)
    return {"device": device_payload(device)}


@router.post("/readings")
def receive_reading(payload: IoTReadingCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Persist telemetry, update the device, and run Provenance Anomaly Detection."""
    product_unit = db.get(ProductUnit, payload.product_unit_id)
    if product_unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")

    now = datetime.now(timezone.utc)
    device = db.scalar(select(IotDevice).where(IotDevice.device_uid == payload.device_uid))
    if device is None:
        device = IotDevice(
            device_uid=payload.device_uid,
            product_unit_id=payload.product_unit_id,
            device_status=DeviceStatus.ACTIVE,
        )
        db.add(device)
        db.flush()
    elif device.product_unit_id != payload.product_unit_id:
        raise HTTPException(status_code=409, detail="Device is bound to another product unit")

    device.device_status = DeviceStatus.ACTIVE
    device.last_seen_at = now
    reading = IotReading(
        device_id=device.id,
        product_unit_id=payload.product_unit_id,
        timestamp=now,
        temperature=payload.temperature,
        humidity=payload.humidity,
        accel_x=payload.accel_x,
        accel_y=payload.accel_y,
        accel_z=payload.accel_z,
        accel_magnitude=payload.accel_magnitude,
    )
    db.add(reading)
    ai_result = score_iot_reading(payload.temperature, payload.accel_magnitude)
    if ai_result["risk_score"] >= 35:
        db.add(
            ProvenanceFlag(
                product_unit_id=payload.product_unit_id,
                risk_score=ai_result["risk_score"],
                reason=ai_result["reason"],
                feature_values=ai_result["feature_values"],
                model_version=ai_result["model_version"],
            )
        )
    db.commit()
    db.refresh(reading)
    return {
        "reading": reading_payload(reading),
        "device": device_payload(device),
        "ai_result": ai_result,
        "status": "accepted",
    }


@router.post("/ai-score")
def score_reading(reading: dict[str, Any]) -> dict[str, Any]:
    """Run the deterministic IoT model directly for development inspection."""
    return score_iot_reading(float(reading.get("temperature", 0)), float(reading.get("accel_magnitude", 0)))


@router.get("/readings")
def list_readings(db: Session = Depends(get_db)) -> dict[str, Any]:
    readings = db.scalars(select(IotReading).order_by(desc(IotReading.timestamp)).limit(100)).all()
    return {"items": [reading_payload(reading) for reading in readings], "total": len(readings)}


@router.get("/summary")
def telemetry_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return every product with its latest available physical-evidence reading."""
    latest_timestamp = (
        select(
            IotReading.product_unit_id,
            func.max(IotReading.timestamp).label("latest_timestamp"),
        )
        .group_by(IotReading.product_unit_id)
        .subquery()
    )
    rows = db.execute(
        select(ProductUnit, IotReading)
        .outerjoin(
            latest_timestamp,
            latest_timestamp.c.product_unit_id == ProductUnit.id,
        )
        .outerjoin(
            IotReading,
            and_(
                IotReading.product_unit_id == ProductUnit.id,
                IotReading.timestamp == latest_timestamp.c.latest_timestamp,
            ),
        )
        .order_by(ProductUnit.id)
    ).all()

    return {
        "items": [
            {
                "unit": {
                    "id": unit.id,
                    "product_name": unit.product_name,
                    "serial_no": unit.serial_no,
                    "qr_public_token": unit.qr_public_token,
                    "risk_score": float(unit.risk_score),
                    "risk_level": unit.risk_level,
                },
                "reading": reading_payload(reading) if reading else None,
            }
            for unit, reading in rows
        ],
        "total": len(rows),
        "with_reading": sum(1 for _, reading in rows if reading is not None),
    }


@router.get("/devices")
def list_devices(db: Session = Depends(get_db)) -> dict[str, Any]:
    devices = db.scalars(select(IotDevice).order_by(IotDevice.device_uid)).all()
    return {"items": [device_payload(device) for device in devices], "total": len(devices)}


@router.get("/devices/{device_uid}")
def get_device(device_uid: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    device = db.scalar(select(IotDevice).where(IotDevice.device_uid == device_uid))
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device": device_payload(device)}


@router.get("/{product_unit_id}/readings")
def unit_readings(product_unit_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    readings = db.scalars(
        select(IotReading)
        .where(IotReading.product_unit_id == product_unit_id)
        .order_by(desc(IotReading.timestamp))
    ).all()
    return {"items": [reading_payload(reading) for reading in readings], "total": len(readings)}


@router.get("/{product_unit_id}/latest")
def latest_unit_reading(product_unit_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    reading = db.scalar(
        select(IotReading)
        .where(IotReading.product_unit_id == product_unit_id)
        .order_by(desc(IotReading.timestamp))
        .limit(1)
    )
    if reading is None:
        raise HTTPException(status_code=404, detail="No IoT readings found for product unit")
    return {"reading": reading_payload(reading)}


@router.get("/")
def health_check() -> dict[str, str]:
    return {"router": "iot", "status": "ok"}