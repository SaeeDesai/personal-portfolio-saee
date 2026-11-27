from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AnalyticsEvent
from backend.schemas import AnalyticsEventCreate

app = FastAPI(
    title="PortfolioPulse API",
    description="Privacy-conscious portfolio analytics platform",
    version="0.1.0",
)


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