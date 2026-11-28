
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import distinct, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth import require_admin, verify_auth_origin
from backend.campaign_schemas import (
    CampaignCreate,
    CampaignMetrics,
    CampaignResponse,
    CampaignWithMetrics,
    generate_campaign_token,
)
from backend.database import get_db
from backend.models import AnalyticsEvent, Campaign


router = APIRouter(
    prefix="/analytics/managed-campaigns",
    tags=["Managed Campaigns"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_auth_origin)],
)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
):
    campaign = Campaign(
        **payload.model_dump(),
        public_token=generate_campaign_token(),
    )

    try:
        db.add(campaign)
        db.flush()

        result = CampaignResponse.model_validate(campaign)

        db.commit()
        return result

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to create campaign",
        )


@router.get(
    "",
    response_model=list[CampaignWithMetrics],
)
def list_campaigns(
    days: int = Query(default=7, ge=1, le=365),
    state: Literal["active", "archived", "all"] = "active",
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    events = AnalyticsEvent

    def count_event(event_type):
        return func.count(events.id).filter(
            events.event_type == event_type
        )

    campaign_metrics = (
        select(
            events.campaign_id.label("campaign_id"),

            func.count(
                distinct(events.session_id)
            ).label("sessions"),

            count_event("page_view").label("page_views"),

            count_event("resume_click").label(
                "resume_clicks"
            ),

            func.count(
                distinct(events.session_id)
            ).filter(
                events.event_type == "resume_click"
            ).label("resume_click_sessions"),

            count_event("project_click").label(
                "project_clicks"
            ),

            count_event("publication_click").label(
                "publication_clicks"
            ),

            count_event("contact_click").label(
                "contact_clicks"
            ),
        )
        .where(
            events.campaign_id.is_not(None),
            events.created_at >= since,
            events.created_at <= now,
        )
        .group_by(events.campaign_id)
        .subquery()
    )

    query = (
        select(
            Campaign,
            campaign_metrics.c.sessions,
            campaign_metrics.c.page_views,
            campaign_metrics.c.resume_clicks,
            campaign_metrics.c.resume_click_sessions,
            campaign_metrics.c.project_clicks,
            campaign_metrics.c.publication_clicks,
            campaign_metrics.c.contact_clicks,
        )
        .outerjoin(
            campaign_metrics,
            Campaign.id == campaign_metrics.c.campaign_id,
        )
    )

    if state == "active":
        query = query.where(
            Campaign.archived_at.is_(None)
        )

    elif state == "archived":
        query = query.where(
            Campaign.archived_at.is_not(None)
        )

    query = (
        query.order_by(
            Campaign.created_at.desc(),
            Campaign.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(query).all()
    results = []

    for row in rows:
        sessions = row.sessions or 0

        resume_click_sessions = (
            row.resume_click_sessions or 0
        )

        metrics = CampaignMetrics(
            sessions=sessions,
            page_views=row.page_views or 0,
            resume_clicks=row.resume_clicks or 0,
            resume_click_sessions=resume_click_sessions,
            project_clicks=row.project_clicks or 0,
            publication_clicks=row.publication_clicks or 0,
            contact_clicks=row.contact_clicks or 0,
            resume_conversion_rate=(
                round(
                    resume_click_sessions / sessions * 100,
                    2,
                )
                if sessions else 0.0
            ),
        )

        results.append(
            CampaignWithMetrics(
                **CampaignResponse.model_validate(
                    row[0]
                ).model_dump(),
                metrics=metrics,
            )
        )

    return results


@router.post(
    "/{campaign_id}/archive",
    response_model=CampaignResponse,
    dependencies=[Depends(verify_auth_origin)],
)
def archive_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        campaign = db.scalar(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .with_for_update()
        )

        if campaign is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found",
            )

        if campaign.archived_at is None:
            campaign.archived_at = datetime.now(
                timezone.utc
            )

        db.flush()

        result = CampaignResponse.model_validate(campaign)

        db.commit()
        return result

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to archive campaign",
        )
