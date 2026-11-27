import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )

    page_path: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    event_target: Mapped[str | None] = mapped_column(String(150))
    referrer_domain: Mapped[str | None] = mapped_column(String(253))

    utm_source: Mapped[str | None] = mapped_column(String(100))
    utm_medium: Mapped[str | None] = mapped_column(String(100))
    utm_campaign: Mapped[str | None] = mapped_column(String(150))

    device_type: Mapped[str | None] = mapped_column(String(10))
    country_code: Mapped[str | None] = mapped_column(String(2))

    scroll_depth: Mapped[int | None] = mapped_column(Integer)
    active_seconds: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "scroll_depth BETWEEN 0 AND 100",
            name="ck_scroll_depth",
        ),
        CheckConstraint(
            "active_seconds >= 0",
            name="ck_active_seconds",
        ),
        CheckConstraint(
            "device_type IN ('desktop', 'mobile', 'tablet', 'unknown')",
            name="ck_device_type",
        ),
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_session_id", "session_id"),
        Index("ix_events_type_created_at", "event_type", "created_at"),
    )