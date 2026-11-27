import pytest
from pydantic import ValidationError

from backend.schemas import AnalyticsEventCreate


BASE_EVENT = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "page_path": "/personal-portfolio-saee/",
}


def test_allowed_project():
    event = AnalyticsEventCreate(
        **BASE_EVENT,
        event_type="project_click",
        event_target="inference_reliability_gateway",
    )

    assert event.event_target == "inference_reliability_gateway"


def test_unknown_target_rejected():
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(
            **BASE_EVENT,
            event_type="project_click",
            event_target="someone@example.com",
        )


def test_referrer_normalized():
    event = AnalyticsEventCreate(
        **BASE_EVENT,
        event_type="page_view",
        referrer_domain="WWW.LinkedIn.com",
    )

    assert event.referrer_domain == "linkedin.com"


def test_raw_referrer_url_not_stored():
    event = AnalyticsEventCreate(
        **BASE_EVENT,
        event_type="page_view",
        referrer_domain="https://example.com/private?id=123",
    )

    assert event.referrer_domain == "other"


def test_campaign_sanitization():
    event = AnalyticsEventCreate(
        **BASE_EVENT,
        event_type="page_view",
        utm_source="LinkedIn",
        utm_medium="social",
        utm_campaign="someone@example.com",
    )

    assert event.utm_source == "linkedin"
    assert event.utm_medium == "social"
    assert event.utm_campaign == "other"