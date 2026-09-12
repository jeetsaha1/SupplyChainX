import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models.tables import ProductUnit
from app.schemas.core import ProductUnitCreate
from app.services.blockchain_service import register_unit_on_chain


router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: ProductUnitCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("admin", "manufacturer")),
) -> dict[str, Any]:
    unit = ProductUnit(
        product_hash=secrets.token_hex(32),
        qr_public_token=secrets.token_urlsafe(24),
        gtin=payload.gtin,
        batch_no=payload.batch_no,
        serial_no=payload.serial_no,
        product_name=payload.product_name,
        expiry_date=payload.expiry_date,
        manufacturer_org_id=payload.manufacturer_org_id,
        current_custodian_org_id=payload.current_custodian_org_id,
        status="created",
        risk_level="low",
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    register_unit_on_chain(unit.product_hash)
    return {"unit": unit_payload(unit)}


def unit_payload(unit: ProductUnit) -> dict[str, Any]:
    return {
        "id": unit.id,
        "product_hash": unit.product_hash,
        "qr_public_token": unit.qr_public_token,
        "gtin": unit.gtin,
        "batch_no": unit.batch_no,
        "serial_no": unit.serial_no,
        "product_name": unit.product_name,
        "expiry_date": unit.expiry_date.isoformat(),
        "status": unit.status,
        "risk_score": float(unit.risk_score),
        "risk_level": unit.risk_level,
        "scan_count": unit.scan_count,
    }


@router.get("/{qr_public_token}")
def get_unit(qr_public_token: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    unit = db.scalar(select(ProductUnit).where(ProductUnit.qr_public_token == qr_public_token))
    if unit is None:
        raise HTTPException(status_code=404, detail="Product unit not found")
    return {"unit": unit_payload(unit)}


@router.get("/")
def list_units(db: Session = Depends(get_db)) -> dict[str, Any]:
    units = db.scalars(select(ProductUnit).order_by(ProductUnit.id)).all()
    return {"items": [unit_payload(unit) for unit in units], "total": len(units)}