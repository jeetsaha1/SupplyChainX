from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductUnitCreate(BaseModel):
    gtin: str = Field(min_length=1)
    batch_no: str = Field(min_length=1)
    serial_no: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    expiry_date: date
    manufacturer_org_id: int
    current_custodian_org_id: int


class LifecycleEventCreate(BaseModel):
    product_unit_id: int
    event_type: str
    location_label: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    organization_id: int
    created_at: datetime
