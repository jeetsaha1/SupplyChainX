from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IoTDeviceCreate(BaseModel):
    device_uid: str = Field(min_length=1)
    product_unit_id: int


class IoTDeviceResponse(IoTDeviceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_status: str
    last_seen_at: datetime | None = None
    created_at: datetime


class IoTReadingCreate(BaseModel):
    device_uid: str = Field(min_length=1)
    product_unit_id: int
    temperature: float
    humidity: float
    accel_x: float
    accel_y: float
    accel_z: float
    accel_magnitude: float


class IoTReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    product_unit_id: int
    timestamp: datetime
    temperature: float
    humidity: float
    accel_x: float
    accel_y: float
    accel_z: float
    accel_magnitude: float
    created_at: datetime