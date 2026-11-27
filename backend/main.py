from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from backend.database import get_db
from backend.models import AnalyticsEvent
from backend.schemas import AnalyticsEventCreate
from backend.analytics import router as analytics_router

app = FastAPI(
    title="PortfolioPulse API",
    description="Privacy-conscious portfolio analytics platform",
    version="0.1.0",
)

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

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "portfoliopulse"
    }


@app.post("/events", status_code=status.HTTP_201_CREATED)
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