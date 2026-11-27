from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from backend.database import get_db
from backend.models import AnalyticsEvent
from backend.schemas import AnalyticsEventCreate
from backend.analytics import router as analytics_router
from backend.auth_routes import router as auth_router
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi import Request
from fastapi.responses import RedirectResponse
from backend.auth import require_admin
from backend.security import (
    enforce_event_rate_limit,
    verify_event_origin,
)
from backend.security import RequestSizeLimitMiddleware
from backend.config import validate_production_config

validate_production_config()

app = FastAPI(
    title="PortfolioPulse API",
    description="Privacy-conscious portfolio analytics platform",
    version="0.1.0",
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=8192,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )

    response.headers["X-Robots-Tag"] = "noindex, nofollow"

    if (
        request.url.path in {"/dashboard", "/login"}
        or request.url.path.startswith("/analytics/")
        or request.url.path.startswith("/auth/")
    ):
        response.headers["Cache-Control"] = "no-store"

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "object-src 'none'"
        )

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://saeedesai.github.io",
    ],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

app.include_router(analytics_router)
app.include_router(auth_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "portfoliopulse"
    }


@app.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(verify_event_origin),
        Depends(enforce_event_rate_limit),
    ],
)

def create_event(
    event: AnalyticsEventCreate,
    db: Session = Depends(get_db),
):
    db_event = AnalyticsEvent(**event.model_dump())

    try:
        db.add(db_event)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Unable to store analytics event",
        )

    return {"status": "accepted"}

DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"

PUBLIC_ASSETS = {
    "style.css",
    "login.js",
    "dashboard.js",
    "vendor/chart.umd.min.js",
}


@app.get("/dashboard-assets/{asset_path:path}", include_in_schema=False)
def dashboard_assets(asset_path: str):
    if asset_path not in PUBLIC_ASSETS:
        raise HTTPException(status_code=404)

    return FileResponse(DASHBOARD_DIR / asset_path)


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(
        DASHBOARD_DIR / "login.html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/dashboard", include_in_schema=False)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        require_admin(request, db)
    except HTTPException as error:
        if error.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

    return FileResponse(
        DASHBOARD_DIR / "index.html",
        headers={"Cache-Control": "no-store"},
    )