
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from backend.main import app

from backend.models import AnalyticsEvent
from backend.security import (
    event_attempts,
    event_lock,
    session_attempts,
)
from backend.tests.test_auth import (
    auth_client,
    sign_in,
    ORIGIN,
)
from backend.tests.test_integration import integration_db


CAMPAIGNS_URL = "/analytics/managed-campaigns"

ADMIN_HEADERS = {
    "Origin": ORIGIN,
}

EVENT_HEADERS = {
    "Origin": "https://saeedesai.github.io",
}

VALID_CAMPAIGN = {
    "company": "Example AI",
    "role": "Machine Learning Engineer",
    "channel": "job_application",
}


@pytest.fixture(autouse=True)
def reset_event_limits():
    with event_lock:
        event_attempts.clear()
        session_attempts.clear()

    yield

    with event_lock:
        event_attempts.clear()
        session_attempts.clear()


@pytest.fixture
def admin_client(auth_client):
    assert sign_in(auth_client).status_code == 200
    return auth_client


def create_campaign(client, **fields):
    response = client.post(
        CAMPAIGNS_URL,
        json={**VALID_CAMPAIGN, **fields},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 201
    return response.json()


def send_event(
    client,
    session_id,
    event_type="page_view",
    **fields,
):
    return client.post(
        "/events",
        json={
            "session_id": str(session_id),
            "event_type": event_type,
            "page_path": "/personal-portfolio-saee/",
            **fields,
        },
        headers=EVENT_HEADERS,
    )


def get_campaign(client, campaign_id, days=7, state="all"):
    response = client.get(
        CAMPAIGNS_URL,
        params={
            "days": days,
            "state": state,
        },
    )

    assert response.status_code == 200

    return next(
        campaign
        for campaign in response.json()
        if campaign["id"] == campaign_id
    )


def archive_campaign(client, campaign_id):
    response = client.post(
        f"{CAMPAIGNS_URL}/{campaign_id}/archive",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200
    return response.json()


def test_unauthenticated_campaign_listing(auth_client):
    response = auth_client.get(CAMPAIGNS_URL)
    assert response.status_code == 401


def test_unauthenticated_campaign_creation(auth_client):
    response = auth_client.post(
        CAMPAIGNS_URL,
        json=VALID_CAMPAIGN,
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 401


def test_unauthenticated_archiving(auth_client):
    response = auth_client.post(
        f"{CAMPAIGNS_URL}/{uuid4()}/archive",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 401


@pytest.mark.parametrize("origin", [
    "https://untrusted.example",
    None,
])
def test_creation_requires_trusted_origin(admin_client, origin):
    headers = {"Origin": origin} if origin else {}

    response = admin_client.post(
        CAMPAIGNS_URL,
        json=VALID_CAMPAIGN,
        headers=headers,
    )

    assert response.status_code == 403


def test_archiving_requires_trusted_origin(admin_client):
    campaign = create_campaign(admin_client)

    response = admin_client.post(
        f"{CAMPAIGNS_URL}/{campaign['id']}/archive",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403


def test_create_and_list_campaign(admin_client):
    campaign = create_campaign(admin_client)

    assert campaign["company"] == "Example AI"
    assert campaign["public_token"].startswith("pp_")
    assert len(campaign["public_token"]) == 46
    assert campaign["archived_at"] is None

    response = admin_client.get(CAMPAIGNS_URL)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"

    item = get_campaign(admin_client, campaign["id"])

    assert item["metrics"]["sessions"] == 0
    assert item["metrics"]["resume_conversion_rate"] == 0


def test_campaign_tokens_are_unique(admin_client):
    first = create_campaign(admin_client)
    second = create_campaign(admin_client)

    assert first["id"] != second["id"]
    assert first["public_token"] != second["public_token"]


def test_invalid_campaign_creation(admin_client):
    response = admin_client.post(
        CAMPAIGNS_URL,
        json={**VALID_CAMPAIGN, "company": "  "},
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 422


def test_campaign_request_body_limit(admin_client):
    response = admin_client.post(
        CAMPAIGNS_URL,
        json={
            **VALID_CAMPAIGN,
            "company": "x" * 9000,
        },
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 413



def test_public_event_does_not_expose_private_labels(
    admin_client,
):
    campaign = create_campaign(admin_client)

    with TestClient(app) as public_client:
        response = send_event(
            public_client,
            uuid4(),
            campaign_token=campaign["public_token"],
        )

        assert response.status_code == 201
        assert response.json() == {"status": "accepted"}
        assert campaign["company"] not in response.text
        assert campaign["role"] not in response.text

        private_response = public_client.get(CAMPAIGNS_URL)

        assert private_response.status_code == 401
        assert campaign["company"] not in private_response.text
        assert campaign["role"] not in private_response.text



def test_valid_campaign_attribution(
    admin_client,
    integration_db,
):
    campaign = create_campaign(admin_client)
    session_id = uuid4()

    response = send_event(
        admin_client,
        session_id,
        campaign_token=campaign["public_token"],
        utm_source="linkedin",
    )

    assert response.status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id
            )
        )

        assert str(event.campaign_id) == campaign["id"]
        assert event.utm_source == "linkedin"


@pytest.mark.parametrize("token", [
    None,
    "malformed",
    "pp_" + "a" * 43,
    123,
])
def test_unrecognized_campaign_keeps_event(
    admin_client,
    integration_db,
    token,
):
    session_id = uuid4()

    response = send_event(
        admin_client,
        session_id,
        campaign_token=token,
        utm_source="linkedin",
        utm_medium="social",
        utm_campaign="portfolio_test",
    )

    assert response.status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id
            )
        )

        assert event.campaign_id is None
        assert event.utm_source == "linkedin"
        assert event.utm_medium == "social"
        assert event.utm_campaign == "portfolio_test"


def test_legacy_event_without_token(
    admin_client,
    integration_db,
):
    session_id = uuid4()

    response = send_event(admin_client, session_id)

    assert response.status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id
            )
        )

        assert event.campaign_id is None


def test_archived_campaign_preserves_history(
    admin_client,
    integration_db,
):
    campaign = create_campaign(admin_client)
    token = campaign["public_token"]

    assert send_event(
        admin_client,
        uuid4(),
        campaign_token=token,
    ).status_code == 201

    archived = archive_campaign(
        admin_client,
        campaign["id"],
    )

    assert archived["archived_at"] is not None

    new_session = uuid4()

    assert send_event(
        admin_client,
        new_session,
        campaign_token=token,
    ).status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == new_session
            )
        )

        assert event.campaign_id is None

    item = get_campaign(admin_client, campaign["id"])

    assert item["metrics"]["sessions"] == 1
    assert item["metrics"]["page_views"] == 1


def test_archive_is_idempotent(admin_client):
    campaign = create_campaign(admin_client)

    first = archive_campaign(
        admin_client,
        campaign["id"],
    )

    second = archive_campaign(
        admin_client,
        campaign["id"],
    )

    assert first["archived_at"] == second["archived_at"]


def test_archive_unknown_campaign(admin_client):
    response = admin_client.post(
        f"{CAMPAIGNS_URL}/{uuid4()}/archive",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 404


def test_campaign_filters(admin_client):
    active = create_campaign(admin_client)
    archived = create_campaign(admin_client)

    archive_campaign(admin_client, archived["id"])

    for state in ("active", "archived", "all"):
        response = admin_client.get(
            CAMPAIGNS_URL,
            params={"state": state},
        )

        assert response.status_code == 200

        ids = {
            campaign["id"]
            for campaign in response.json()
        }

        assert (active["id"] in ids) == (
            state in ("active", "all")
        )

        assert (archived["id"] in ids) == (
            state in ("archived", "all")
        )


def test_resume_conversion_uses_distinct_sessions(
    admin_client,
):
    campaign = create_campaign(admin_client)
    token = campaign["public_token"]

    first_session = uuid4()
    second_session = uuid4()

    for session_id in (first_session, second_session):
        assert send_event(
            admin_client,
            session_id,
            campaign_token=token,
        ).status_code == 201

    for _ in range(3):
        assert send_event(
            admin_client,
            first_session,
            event_type="resume_click",
            event_target="resume",
            campaign_token=token,
        ).status_code == 201

    item = get_campaign(admin_client, campaign["id"])
    metrics = item["metrics"]

    assert metrics["sessions"] == 2
    assert metrics["page_views"] == 2
    assert metrics["resume_clicks"] == 3
    assert metrics["resume_click_sessions"] == 1
    assert metrics["resume_conversion_rate"] == 50.0


def test_same_session_multiple_campaigns(
    admin_client,
    integration_db,
):
    first = create_campaign(admin_client)
    second = create_campaign(admin_client)

    session_id = uuid4()

    for campaign in (first, second):
        assert send_event(
            admin_client,
            session_id,
            campaign_token=campaign["public_token"],
        ).status_code == 201

    assert send_event(
        admin_client,
        session_id,
        event_type="resume_click",
        event_target="resume",
        campaign_token=second["public_token"],
    ).status_code == 201

    assert send_event(
        admin_client,
        session_id,
        event_type="project_click",
        event_target="inference_reliability_gateway",
    ).status_code == 201

    first_metrics = get_campaign(
        admin_client,
        first["id"],
    )["metrics"]

    second_metrics = get_campaign(
        admin_client,
        second["id"],
    )["metrics"]

    assert first_metrics["sessions"] == 1
    assert first_metrics["resume_clicks"] == 0

    assert second_metrics["sessions"] == 1
    assert second_metrics["resume_clicks"] == 1
    assert second_metrics["resume_conversion_rate"] == 100

    assert first_metrics["project_clicks"] == 0
    assert second_metrics["project_clicks"] == 0

    with integration_db() as db:
        untagged_event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id,
                AnalyticsEvent.event_type == "project_click",
            )
        )

        assert untagged_event.campaign_id is None


def test_campaign_metrics_respect_date_range(
    admin_client,
    integration_db,
):
    campaign = create_campaign(admin_client)

    old_session = uuid4()
    recent_session = uuid4()

    for session_id in (old_session, recent_session):
        assert send_event(
            admin_client,
            session_id,
            campaign_token=campaign["public_token"],
        ).status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == old_session
            )
        )

        event.created_at = (
            datetime.now(timezone.utc)
            - timedelta(days=10)
        )

        db.commit()

    seven_days = get_campaign(
        admin_client,
        campaign["id"],
        days=7,
    )["metrics"]

    thirty_days = get_campaign(
        admin_client,
        campaign["id"],
        days=30,
    )["metrics"]

    assert seven_days["sessions"] == 1
    assert thirty_days["sessions"] == 2


@pytest.mark.parametrize("params", [
    {"days": 0},
    {"days": 366},
    {"state": "invalid"},
    {"limit": 101},
    {"offset": -1},
])
def test_invalid_listing_parameters(admin_client, params):
    response = admin_client.get(
        CAMPAIGNS_URL,
        params=params,
    )

    assert response.status_code == 422


def test_campaign_pagination(admin_client):
    campaigns = [
        create_campaign(
            admin_client,
            company=f"Example Company {number}",
        )
        for number in range(3)
    ]

    first_page = admin_client.get(
        CAMPAIGNS_URL,
        params={"limit": 2, "offset": 0},
    )

    second_page = admin_client.get(
        CAMPAIGNS_URL,
        params={"limit": 2, "offset": 2},
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    first_items = first_page.json()
    second_items = second_page.json()

    assert len(first_items) == 2
    assert len(second_items) == 1

    first_ids = {
        item["id"] for item in first_items
    }

    second_ids = {
        item["id"] for item in second_items
    }

    expected_ids = {
        item["id"] for item in campaigns
    }

    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == expected_ids
