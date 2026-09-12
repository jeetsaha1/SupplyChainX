from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.tables import User
from app.schemas.core import LoginRequest, TokenResponse


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))


@router.get("/me")
def current_user(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role.value,
            "organization_id": user.organization_id,
            "created_at": user.created_at.isoformat(),
        }
    }


@router.get("/")
def health_check() -> dict[str, str]:
    return {"router": "auth", "status": "ok"}