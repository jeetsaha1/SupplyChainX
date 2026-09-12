"""Load the existing CSV datasets through SQLAlchemy ORM only."""

import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, create_tables  # noqa: E402
from app.models.tables import (  # noqa: E402
    ChainStatus,
    EventType,
    DeviceStatus,
    IotDevice,
    IotReading,
    LifecycleEvent,
    Organization,
    OrganizationType,
    ProductUnit,
    ProvenanceFlag,
    User,
    UserRole,
    VerificationEvent,
)

DATASETS = ROOT.parent / "datasets"
ZERO_HASH = "0" * 64
DEFAULT_EXPIRY_DATE = date(2099, 12, 31)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace(" ", "T").replace("+0000", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_rows(filename: str) -> list[dict[str, str]]:
    with (DATASETS / filename).open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def parse_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def upsert(session, model, primary_key: int, values: dict):
    instance = session.get(model, primary_key)
    if instance is None:
        instance = model(id=primary_key, **values)
        session.add(instance)
    else:
        for key, value in values.items():
            setattr(instance, key, value)
    return instance


def load_datasets() -> None:
    create_tables()
    with SessionLocal() as session:
        for row in read_rows("organizations.csv"):
            upsert(session, Organization, int(row["id"]), {
                "name": row["name"],
                "org_type": OrganizationType(row["org_type"]),
                "created_at": parse_datetime(row["created_at"]) or datetime.now(timezone.utc),
            })

        for row in read_rows("users.csv"):
            organization_id = int(row["organization_id"]) if row.get("organization_id") else 1
            role = row.get("role") or "admin"
            upsert(session, User, int(row["id"]), {
                "email": row["email"],
                "password_hash": row.get("password_hash") or "dataset-placeholder-hash",
                "role": UserRole(role),
                "organization_id": organization_id,
                "created_at": parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            })

        for row in read_rows("product_units_seed.csv"):
            values = {
                "product_hash": row["product_hash"],
                "qr_public_token": row["qr_public_token"],
                "gtin": row["gtin"],
                "batch_no": row["batch_no"],
                "serial_no": row["serial_no"],
                "product_name": row["product_name"],
                "expiry_date": date.fromisoformat(row["expiry_date"]) if row.get("expiry_date") else DEFAULT_EXPIRY_DATE,
                "manufacturer_org_id": int(row["manufacturer_org_id"]),
                "current_custodian_org_id": int(row["current_custodian_org_id"]),
                "status": row["status"],
                "risk_score": float(row.get("risk_score") or 0),
                "risk_level": (row.get("risk_level") or "low").lower(),
                "scan_count": int(row.get("scan_count") or 0),
                "last_verified_at": parse_datetime(row.get("last_verified_at")),
                "created_at": parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            }
            upsert(session, ProductUnit, int(row["id"]), values)

        for row in read_rows("lifecycle_events.csv"):
            upsert(session, LifecycleEvent, int(row["id"]), {
                "product_unit_id": int(row["product_unit_id"]),
                "actor_id": int(row["actor_id"]) if row.get("actor_id") else None,
                "actor_organization_id": int(row["actor_organization_id"]) if row.get("actor_organization_id") else None,
                "event_type": EventType(row["event_type"]),
                "location_label": row.get("location_label") or None,
                "latitude": float(row["latitude"]) if row.get("latitude") else None,
                "longitude": float(row["longitude"]) if row.get("longitude") else None,
                "timestamp": parse_datetime(row["timestamp"]),
                "event_hash": row["event_hash"],
                "previous_event_hash": row.get("previous_event_hash") or ZERO_HASH,
                "tx_hash": row.get("tx_hash") or None,
                "chain_status": ChainStatus(row.get("chain_status", "simulated")),
                "idempotency_key": row["idempotency_key"],
                "metadata_": parse_json(row.get("metadata")),
                "created_at": parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            })

        for row in read_rows("verification_events.csv"):
            upsert(session, VerificationEvent, int(row["id"]), {
                "product_unit_id": int(row["product_unit_id"]),
                "result": row["result"],
                "ip_hash": row["ip_hash"],
                "user_agent_hash": row["user_agent_hash"],
                "created_at": parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            })

        flags_file = DATASETS / "provenance_flags (3).csv"
        if flags_file.exists():
            for row in read_rows(flags_file.name):
                upsert(session, ProvenanceFlag, int(row["id"]), {
                    "product_unit_id": int(row["product_unit_id"]),
                    "event_id": int(row["event_id"]) if row.get("event_id") else None,
                    "risk_score": float(row["risk_score"]) if row.get("risk_score") else 0.0,
                    "reason": row["reason"],
                    "feature_values": parse_json(row.get("feature_values")),
                    "model_version": row.get("model_version") or "dataset",
                    "created_at": parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
                })

        # Give every seeded medicine a baseline physical-evidence record so the
        # integrated demo can show all products before live Arduino readings arrive.
        product_units = session.scalars(select(ProductUnit).order_by(ProductUnit.id)).all()
        for unit in product_units:
            device_uid = f"SCX-DEMO-{unit.id:04d}"
            device = session.scalar(select(IotDevice).where(IotDevice.device_uid == device_uid))
            if device is None:
                device = IotDevice(
                    device_uid=device_uid,
                    product_unit_id=unit.id,
                    device_status=DeviceStatus.ACTIVE,
                    last_seen_at=datetime.now(timezone.utc),
                )
                session.add(device)
                session.flush()

            existing_reading = session.scalar(
                select(IotReading)
                .where(
                    IotReading.device_id == device.id,
                    IotReading.product_unit_id == unit.id,
                )
                .limit(1)
            )
            if existing_reading is None:
                temperature = 20.0 + (unit.id % 60) / 10
                accel_magnitude = 1.0
                now = datetime.now(timezone.utc)
                session.add(IotReading(
                    device_id=device.id,
                    product_unit_id=unit.id,
                    timestamp=now,
                    temperature=temperature,
                    humidity=50.0 + (unit.id % 20),
                    accel_x=0.0,
                    accel_y=0.0,
                    accel_z=accel_magnitude,
                    accel_magnitude=accel_magnitude,
                    created_at=now,
                ))

        session.commit()
        print("Datasets loaded through SQLAlchemy ORM.")
        print("Product units:", session.scalar(select(ProductUnit).count()) if False else session.query(ProductUnit).count())


if __name__ == "__main__":
    load_datasets()
