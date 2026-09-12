import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tables import ProductUnit, VerificationEvent
from app.routers.units import unit_payload


router = APIRouter()


@router.get("/{qr_public_token}")
def verify_product(
    qr_public_token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    unit = db.scalar(select(ProductUnit).where(ProductUnit.qr_public_token == qr_public_token))
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")

    ip_value = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    ip_hash = hashlib.sha256(ip_value.encode()).hexdigest()
    user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    recent_verification = db.scalar(
        select(VerificationEvent)
        .where(
            VerificationEvent.product_unit_id == unit.id,
            VerificationEvent.ip_hash == ip_hash,
            VerificationEvent.user_agent_hash == user_agent_hash,
            VerificationEvent.created_at >= now - timedelta(seconds=60),
        )
        .order_by(desc(VerificationEvent.created_at))
        .limit(1)
    )
    duplicate = recent_verification is not None
    unit.scan_count += 1
    unit.last_verified_at = now
    db.add(VerificationEvent(
        product_unit_id=unit.id,
        result="success",
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    ))
    db.commit()
    return {
        "unit": unit_payload(unit),
        "verification_event": {"result": "success", "is_duplicate": duplicate},
        "warning": "Repeated scans may indicate label cloning or misuse." if duplicate else None,
    }


@router.get("/")
def health_check() -> dict[str, str]:
    return {"router": "verify", "status": "ok"}