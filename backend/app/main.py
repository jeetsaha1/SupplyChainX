from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.routers import auth, events, iot, units, verify


app = FastAPI(title="SupplyChainX API", version="0.1.0")

create_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "SupplyChainX API", "status": "ok", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health")
def versioned_health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(units.router, prefix="/api/v1/units", tags=["units"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(iot.router, prefix="/api/v1/iot", tags=["iot"])
app.include_router(verify.router, prefix="/api/v1/verify", tags=["verify"])