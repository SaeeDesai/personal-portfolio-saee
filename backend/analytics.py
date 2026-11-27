from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AnalyticsEvent

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)

CLICK_EVENTS = (
    "resume_click",
    "github_click",
    "project_click",
    "publication_click",
    "contact_click",
)


@router.get("/summary")
def get_summary(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    events = AnalyticsEvent

    def count_events(event_type):
        return db.scalar(
            select(func.count())
            .select_from(events)
            .where(
                events.created_at >= since,
                events.event_type == event_type,
            )
        ) or 0

    sessions = db.scalar(
        select(func.count(distinct(events.session_id)))
        .where(events.created_at >= since)
    ) or 0

    total_active_seconds = db.scalar(
        select(func.coalesce(func.sum(events.active_seconds), 0))
        .where(
            events.created_at >= since,
            events.event_type == "active_duration",
        )
    )

    engaged_sessions = db.scalar(
        select(func.count(distinct(events.session_id)))
        .where(
            events.created_at >= since,
            events.event_type.in_(CLICK_EVENTS),
        )
    ) or 0

    return {
        "period_days": days,
        "page_views": count_events("page_view"),
        "sessions": sessions,
        "resume_clicks": count_events("resume_click"),
        "project_clicks": count_events("project_click"),
        "github_clicks": count_events("github_click"),
        "publication_clicks": count_events("publication_click"),
        "contact_clicks": count_events("contact_click"),
        "total_active_seconds": total_active_seconds,
        "avg_active_seconds_per_session": (
            round(total_active_seconds / sessions, 2)
            if sessions else 0
        ),
        "engagement_rate": (
            round(engaged_sessions / sessions * 100, 2)
            if sessions else 0
        ),
    }


@router.get("/traffic")
def get_traffic(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    day = func.date(
        func.timezone("UTC", AnalyticsEvent.created_at)
    ).label("date")

    rows = db.execute(
        select(
            day,
            func.count().label("page_views"),
            func.count(
                distinct(AnalyticsEvent.session_id)
            ).label("sessions"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "page_view",
        )
        .group_by(day)
        .order_by(day)
    ).all()

    return [
        {
            "date": row.date.isoformat(),
            "page_views": row.page_views,
            "sessions": row.sessions,
        }
        for row in rows
    ]


@router.get("/referrers")
def get_referrers(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    source = func.coalesce(
        AnalyticsEvent.referrer_domain, "direct_or_unknown"
    ).label("source")

    rows = db.execute(
        select(source, func.count().label("views"))
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "page_view",
        )
        .group_by(source)
        .order_by(func.count().desc())
    ).all()

    return [
        {"source": row.source, "views": row.views}
        for row in rows
    ]


@router.get("/projects")
def get_projects(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.execute(
        select(
            AnalyticsEvent.event_target,
            func.count().label("clicks"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "project_click",
        )
        .group_by(AnalyticsEvent.event_target)
        .order_by(func.count().desc())
    ).all()

    return [
        {
            "project": row.event_target,
            "clicks": row.clicks,
        }
        for row in rows
    ]


@router.get("/devices")
def get_devices(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.execute(
        select(
            AnalyticsEvent.device_type,
            func.count().label("views"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "page_view",
        )
        .group_by(AnalyticsEvent.device_type)
        .order_by(func.count().desc())
    ).all()

    return [
        {
            "device": row.device_type or "unknown",
            "views": row.views,
        }
        for row in rows
    ]

@router.get("/campaigns")
def get_campaigns(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.execute(
        select(
            AnalyticsEvent.utm_source,
            AnalyticsEvent.utm_medium,
            AnalyticsEvent.utm_campaign,
            func.count().label("page_views"),
            func.count(
                distinct(AnalyticsEvent.session_id)
            ).label("sessions"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "page_view",
            AnalyticsEvent.utm_source.is_not(None),
        )
        .group_by(
            AnalyticsEvent.utm_source,
            AnalyticsEvent.utm_medium,
            AnalyticsEvent.utm_campaign,
        )
        .order_by(func.count().desc())
    ).all()

    return [
        {
            "source": row.utm_source,
            "medium": row.utm_medium,
            "campaign": row.utm_campaign,
            "page_views": row.page_views,
            "sessions": row.sessions,
        }
        for row in rows
    ]

@router.get("/publications")
def get_publications(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = db.execute(
        select(
            AnalyticsEvent.event_target,
            func.count().label("clicks"),
        )
        .where(
            AnalyticsEvent.created_at >= since,
            AnalyticsEvent.event_type == "publication_click",
        )
        .group_by(AnalyticsEvent.event_target)
        .order_by(func.count().desc())
    ).all()

    return [
        {
            "publication": row.event_target,
            "clicks": row.clicks,
        }
        for row in rows
    ]

@router.get("/scroll-depth")
def get_scroll_depth(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_sessions = db.scalar(
        select(func.count(distinct(AnalyticsEvent.session_id)))
        .where(AnalyticsEvent.created_at >= since)
    ) or 0

    results = []

    for threshold in (25, 50, 75, 100):
        sessions = db.scalar(
            select(func.count(distinct(AnalyticsEvent.session_id)))
            .where(
                AnalyticsEvent.created_at >= since,
                AnalyticsEvent.event_type == "scroll_depth",
                AnalyticsEvent.scroll_depth >= threshold,
            )
        ) or 0

        results.append({
            "depth": threshold,
            "sessions": sessions,
            "percentage": (
                round(sessions / total_sessions * 100, 2)
                if total_sessions else 0
            ),
        })

    return results