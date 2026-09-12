from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.tables import ChainStatus, EventType, IotReading, LifecycleEvent, ProductUnit, ProvenanceFlag, VerificationEvent
from app.schemas.core import LifecycleEventCreate
from app.services.ai_service import score_event
from app.services.blockchain_service import anchor_event_on_chain
from app.services.hash_chain import hash_event


router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: LifecycleEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict[str, Any]:
    try:
        event_type = EventType(payload.event_type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Unsupported lifecycle event type") from error

    unit = db.get(ProductUnit, payload.product_unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")
    if unit.current_custodian_org_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="User organization is not current custodian")
    if db.scalar(select(LifecycleEvent).where(LifecycleEvent.idempotency_key == payload.idempotency_key)):
        raise HTTPException(status_code=409, detail="Idempotency key already used")

    previous = db.scalar(
        select(LifecycleEvent)
        .where(LifecycleEvent.product_unit_id == unit.id)
        .order_by(desc(LifecycleEvent.timestamp))
    )
    previous_hash = previous.event_hash if previous else "0" * 64
    event_data = payload.model_dump(exclude={"idempotency_key"})
    event_data.update({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "_current_custodian_org_id": unit.current_custodian_org_id,
        "_unit_status": unit.status,
        "actor_organization_id": current_user.organization_id,
    })
    prior_events = [
        {
            "event_type": item.event_type.value,
            "location_label": item.location_label,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "timestamp": item.timestamp.isoformat(),
        }
        for item in db.scalars(
            select(LifecycleEvent)
            .where(LifecycleEvent.product_unit_id == unit.id)
            .order_by(LifecycleEvent.timestamp)
        ).all()
    ]
    iot_readings = [
        {
            "timestamp": item.timestamp.isoformat(),
            "temperature": item.temperature,
            "accel_magnitude": item.accel_magnitude,
        }
        for item in db.scalars(
            select(IotReading)
            .where(IotReading.product_unit_id == unit.id)
            .order_by(IotReading.timestamp)
        ).all()
    ]
    duplicate_scan_count = db.scalar(
        select(func.count(VerificationEvent.id)).where(VerificationEvent.product_unit_id == unit.id)
    ) or 0
    event_hash = hash_event(event_data, previous_hash)
    tx_hash = anchor_event_on_chain(event_hash, unit.product_hash)
    event = LifecycleEvent(
        product_unit_id=unit.id,
        actor_id=current_user.id,
        actor_organization_id=current_user.organization_id,
        event_type=event_type,
        location_label=payload.location_label,
        latitude=payload.latitude,
        longitude=payload.longitude,
        timestamp=datetime.now(timezone.utc),
        event_hash=event_hash,
        previous_event_hash=previous_hash,
        tx_hash=tx_hash,
        chain_status=ChainStatus.SIMULATED,
        idempotency_key=payload.idempotency_key,
        metadata_=payload.metadata,
    )
    db.add(event)
    db.flush()

    ai_result = score_event(event_data, prior_events, iot_readings, duplicate_scan_count)
    unit.risk_score = ai_result["risk_score"]
    unit.risk_level = str(ai_result["risk_level"]).lower()
    if ai_result["risk_score"] >= 35:
        db.add(ProvenanceFlag(
            product_unit_id=unit.id,
            event_id=event.id,
            risk_score=ai_result["risk_score"],
            reason=ai_result["reason"],
            feature_values=ai_result["feature_values"],
            model_version="deterministic-stub",
        ))
    db.commit()
    db.refresh(event)
    return {"event": event_payload(event), "ai_result": ai_result}


def event_payload(event: LifecycleEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "product_unit_id": event.product_unit_id,
        "event_type": event.event_type.value,
        "location_label": event.location_label,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "timestamp": event.timestamp.isoformat(),
        "event_hash": event.event_hash,
        "previous_event_hash": event.previous_event_hash,
        "tx_hash": event.tx_hash,
        "chain_status": event.chain_status.value,
        "metadata": event.metadata_,
    }


@router.get("/{product_unit_id}")
def list_unit_events(product_unit_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    events = db.scalars(
        select(LifecycleEvent)
        .where(LifecycleEvent.product_unit_id == product_unit_id)
        .order_by(LifecycleEvent.timestamp)
    ).all()
    return {"items": [event_payload(event) for event in events], "total": len(events)}


@router.get("/")
def health_check() -> dict[str, str]:
    return {"router": "events", "status": "ok"}