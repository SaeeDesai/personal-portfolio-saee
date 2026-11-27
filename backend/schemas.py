from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnalyticsEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID

    event_type: Literal[
        "page_view",
        "resume_click",
        "github_click",
        "project_click",
        "publication_click",
        "contact_click",
        "scroll_depth",
        "active_duration",
    ]

    page_path: Literal["/personal-portfolio-saee/"]

    event_target: str | None = Field(default=None, max_length=150)
    referrer_domain: str | None = Field(default=None, max_length=253)

    utm_source: str | None = Field(default=None, max_length=100)
    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=150)

    device_type: Literal[
        "desktop", "mobile", "tablet", "unknown"
    ] = "unknown"

    scroll_depth: int | None = Field(default=None, ge=0, le=100)
    active_seconds: int | None = Field(default=None, ge=0, le=86400)

    @model_validator(mode="after")
    def validate_event_fields(self):
        click_events = {
            "resume_click",
            "github_click",
            "project_click",
            "publication_click",
            "contact_click",
        }

        if self.event_type in click_events:
            if not self.event_target or not self.event_target.strip():
                raise ValueError("Click events require an event_target")
        elif self.event_target is not None:
            raise ValueError("event_target is only allowed for click events")

        if self.event_type == "scroll_depth":
            if self.scroll_depth is None:
                raise ValueError("scroll_depth is required")
        elif self.scroll_depth is not None:
            raise ValueError("Unexpected scroll_depth field")

        if self.event_type == "active_duration":
            if self.active_seconds is None:
                raise ValueError("active_seconds is required")
        elif self.active_seconds is not None:
            raise ValueError("Unexpected active_seconds field")

        return self