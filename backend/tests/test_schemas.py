import pytest
from pydantic import ValidationError

from backend.schemas import AnalyticsEventCreate


BASE_EVENT = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "page_path": "/personal-portfolio-saee/",
}


@pytest.mark.parametrize(
    "fields",
    [
        {"event_type": "page_view"},
        {"event_type": "resume_click", "event_target": "resume"},
        {"event_type": "scroll_depth", "scroll_depth": 75},
        {"event_type": "active_duration", "active_seconds": 120},
    ],
)
def test_valid_events(fields):
    event = AnalyticsEventCreate(**BASE_EVENT, **fields)
    assert event.event_type == fields["event_type"]


@pytest.mark.parametrize(
    "fields",
    [
        {"event_type": "unsupported_event"},
        {"event_type": "resume_click"},
        {"event_type": "project_click", "event_target": " "},
        {"event_type": "scroll_depth"},
        {"event_type": "scroll_depth", "scroll_depth": 150},
        {"event_type": "scroll_depth", "scroll_depth": -10},
        {"event_type": "active_duration"},
        {"event_type": "active_duration", "active_seconds": -5},
        {"event_type": "page_view", "scroll_depth": 50},
        {"event_type": "page_view", "event_target": "resume"},
        {"event_type": "page_view", "active_seconds": 30},
        {"event_type": "page_view", "ip_address": "127.0.0.1"},
    ],
)
def test_invalid_events(fields):
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(**BASE_EVENT, **fields)
        