from fastapi.testclient import TestClient
import pytest

from backend.main import app
from backend.tests.test_integration import integration_db
from backend.auth import require_admin
from backend.models import AdminSession

client = TestClient(app)

@pytest.fixture(autouse=True)
def authenticated_admin():
    app.dependency_overrides[require_admin] = lambda: AdminSession()

    yield

    app.dependency_overrides.pop(require_admin, None)

BASE_EVENT = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "page_path": "/personal-portfolio-saee/",
    "device_type": "desktop",
}


def test_summary_aggregation(integration_db):
    events = [
        {"event_type": "page_view"},
        {
            "event_type": "resume_click",
            "event_target": "resume",
        },
        {
            "event_type": "active_duration",
            "active_seconds": 30,
        },
    ]

    for event in events:
        response = client.post(
            "/events",
            json={**BASE_EVENT, **event},
        )
        assert response.status_code == 201

    response = client.get("/analytics/summary")
    assert response.status_code == 200

    data = response.json()

    assert data["page_views"] == 1
    assert data["sessions"] == 1
    assert data["resume_clicks"] == 1
    assert data["total_active_seconds"] == 30
    assert data["avg_active_seconds_per_session"] == 30
    assert data["engagement_rate"] == 100


@pytest.mark.parametrize(
    "endpoint",
    [
        "traffic",
        "referrers",
        "projects",
        "devices",
        "campaigns",
        "publications",
        "scroll-depth",
    ],
)
def test_aggregation_endpoints(endpoint, integration_db):
    response = client.get(f"/analytics/{endpoint}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.parametrize("days", [0, -1, 366])
def test_invalid_date_range(days):
    response = client.get(
        f"/analytics/summary?days={days}"
    )

    assert response.status_code == 422


def test_empty_summary(integration_db):
    response = client.get("/analytics/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["page_views"] == 0
    assert data["sessions"] == 0
    assert data["engagement_rate"] == 0
    assert data["avg_active_seconds_per_session"] == 0