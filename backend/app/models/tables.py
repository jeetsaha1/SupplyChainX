from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enum_values(enum_type: type[Enum]) -> list[str]:
    return [member.value for member in enum_type]


class OrganizationType(str, Enum):
    MANUFACTURER = "manufacturer"
    LOGISTICS = "logistics"
    ADMIN = "admin"


class UserRole(str, Enum):
    ADMIN = "admin"
    MANUFACTURER = "manufacturer"
    LOGISTICS = "logistics"


class EventType(str, Enum):
    MANUFACTURED = "manufactured"
    INSPECTED = "inspected"
    SHIPPED = "shipped"
    RECEIVED = "received"
    SOLD = "sold"


class ChainStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    SIMULATED = "simulated"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    OFFLINE = "offline"
    STALE = "stale"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[OrganizationType] = mapped_column(SqlEnum(OrganizationType, values_callable=enum_values), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole, values_callable=enum_values), nullable=False)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ProductUnit(Base):
    __tablename__ = "product_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    qr_public_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    gtin: Mapped[str] = mapped_column(String(14), nullable=False)
    batch_no: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_no: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    expiry_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    manufacturer_org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    current_custodian_org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    scan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_product_units_risk_score"),
        CheckConstraint("scan_count >= 0", name="ck_product_units_scan_count"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_product_units_risk_level"),
    )


class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_unit_id: Mapped[int] = mapped_column(ForeignKey("product_units.id"), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    actor_organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    event_type: Mapped[EventType] = mapped_column(SqlEnum(EventType, values_callable=enum_values), nullable=False)
    location_label: Mapped[str | None] = mapped_column(String(255))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_event_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(128))
    chain_status: Mapped[ChainStatus] = mapped_column(SqlEnum(ChainStatus, values_callable=enum_values), nullable=False, default=ChainStatus.SIMULATED)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB().with_variant(JSON, "sqlite"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_lifecycle_events_unit_ts", "product_unit_id", "timestamp"),)


class ProvenanceFlag(Base):
    __tablename__ = "provenance_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_unit_id: Mapped[int] = mapped_column(ForeignKey("product_units.id"), nullable=False)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("lifecycle_events.id"))
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    feature_values: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=False, default=dict
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_provenance_flags_risk_score"),)


class VerificationEvent(Base):
    __tablename__ = "verification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_unit_id: Mapped[int] = mapped_column(ForeignKey("product_units.id"), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_agent_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IotDevice(Base):
    __tablename__ = "iot_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_uid: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    product_unit_id: Mapped[int] = mapped_column(ForeignKey("product_units.id"), nullable=False)
    device_status: Mapped[DeviceStatus] = mapped_column(SqlEnum(DeviceStatus, values_callable=enum_values), nullable=False, default=DeviceStatus.ACTIVE)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IotReading(Base):
    __tablename__ = "iot_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("iot_devices.id"), nullable=False)
    product_unit_id: Mapped[int] = mapped_column(ForeignKey("product_units.id"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)
    accel_x: Mapped[float] = mapped_column(Float, nullable=False)
    accel_y: Mapped[float] = mapped_column(Float, nullable=False)
    accel_z: Mapped[float] = mapped_column(Float, nullable=False)
    accel_magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_iot_readings_unit_ts", "product_unit_id", "timestamp"),)
