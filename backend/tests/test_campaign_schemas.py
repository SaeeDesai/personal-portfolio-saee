
import pytest
from pydantic import ValidationError

from backend.campaign_schemas import (
    CampaignCreate,
    generate_campaign_token,
    normalize_campaign_token,
)
from backend.schemas import AnalyticsEventCreate


VALID_CAMPAIGN = {
    "company": "Example AI",
    "role": "Machine Learning Engineer",
    "channel": "job_application",
}

BASE_EVENT = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "page_view",
    "page_path": "/personal-portfolio-saee/",
}


def test_generated_tokens_have_valid_format():
    token = generate_campaign_token()

    assert token.startswith("pp_")
    assert len(token) == 46
    assert normalize_campaign_token(token) == token


def test_generated_tokens_are_distinct():
    tokens = {
        generate_campaign_token()
        for _ in range(100)
    }

    assert len(tokens) == 100


@pytest.mark.parametrize("value", [
    None,
    "",
    "pp_short",
    "pp_" + "a" * 44,
    "pp_" + "/" * 43,
    "pp_" + "." * 43,
    "pp_" + "a" * 42 + "\n",
    "Example AI",
    123,
    {"token": "invalid"},
])
def test_invalid_tokens_are_discarded(value):
    assert normalize_campaign_token(value) is None


def test_valid_campaign():
    campaign = CampaignCreate(**VALID_CAMPAIGN)

    assert campaign.company == "Example AI"
    assert campaign.channel == "job_application"


def test_campaign_labels_are_trimmed():
    campaign = CampaignCreate(
        **{
            **VALID_CAMPAIGN,
            "company": "  Example AI  ",
            "role": "  AI Engineer  ",
        }
    )

    assert campaign.company == "Example AI"
    assert campaign.role == "AI Engineer"


@pytest.mark.parametrize("fields", [
    {"company": ""},
    {"company": "   "},
    {"company": "a" * 151},
    {"role": ""},
    {"role": "a" * 151},
    {"role": "AI\nEngineer"},
    {"role": 123},
    {"channel": "unsupported"},
    {"public_token": "client_supplied"},
    {"archived_at": None},
])
def test_invalid_campaign_fields(fields):
    with pytest.raises(ValidationError):
        CampaignCreate(**{**VALID_CAMPAIGN, **fields})


def test_legacy_event_remains_valid():
    event = AnalyticsEventCreate(**BASE_EVENT)

    assert event.campaign_token is None


def test_event_accepts_valid_campaign_token():
    token = generate_campaign_token()

    event = AnalyticsEventCreate(
        **BASE_EVENT,
        campaign_token=token,
    )

    assert event.campaign_token == token


def test_malformed_token_does_not_break_event():
    event = AnalyticsEventCreate(
        **BASE_EVENT,
        campaign_token="invalid-campaign",
        utm_source="linkedin",
    )

    assert event.campaign_token is None
    assert event.utm_source == "linkedin"


def test_client_cannot_supply_internal_campaign_id():
    with pytest.raises(ValidationError):
        AnalyticsEventCreate(
            **BASE_EVENT,
            campaign_id=BASE_EVENT["session_id"],
        )
