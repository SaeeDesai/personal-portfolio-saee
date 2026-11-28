
import re
import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


CAMPAIGN_TOKEN_PATTERN = re.compile(
    r"pp_[A-Za-z0-9_-]{43}"
)

CampaignChannel = Literal[
    "job_application",
    "recruiter_outreach",
    "referral",
    "linkedin",
    "networking",
    "other",
]


def generate_campaign_token() -> str:
    """Generate an opaque public attribution identifier."""

    return f"pp_{secrets.token_urlsafe(32)}"


def normalize_campaign_token(value: object) -> str | None:
    """Ignore malformed campaign identifiers without storing them."""

    if not isinstance(value, str):
        return None

    if len(value) != 46:
        return None

    if not CAMPAIGN_TOKEN_PATTERN.fullmatch(value):
        return None

    return value


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=150)
    channel: CampaignChannel

    @field_validator("company", "role", mode="before")
    @classmethod
    def validate_label(cls, value):
        if not isinstance(value, str):
            raise ValueError("Campaign labels must be text")

        if not value.isprintable():
            raise ValueError(
                "Campaign labels must contain printable text"
            )

        value = value.strip()

        if not value:
            raise ValueError("Campaign labels cannot be empty")

        return value


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    public_token: str
    company: str
    role: str
    channel: CampaignChannel
    created_at: datetime
    archived_at: datetime | None


class CampaignMetrics(BaseModel):
    sessions: int = 0
    page_views: int = 0
    resume_clicks: int = 0
    resume_click_sessions: int = 0
    project_clicks: int = 0
    publication_clicks: int = 0
    contact_clicks: int = 0
    resume_conversion_rate: float = 0.0


class CampaignWithMetrics(CampaignResponse):
    metrics: CampaignMetrics
