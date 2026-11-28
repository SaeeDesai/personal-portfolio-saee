import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import event_attempts
from backend.tests.test_events import mock_db, VALID_EVENT


client = TestClient(app)

TRUSTED_ORIGIN = "https://saeedesai.github.io"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    event_attempts.clear()
    yield
    event_attempts.clear()


def test_untrusted_event_origin(mock_db):
    response = client.post(
        "/events",
        json=VALID_EVENT,
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403
    mock_db.add.assert_not_called()


def test_missing_event_origin(mock_db):
    response = client.post(
        "/events",
        json=VALID_EVENT,
    )

    assert response.status_code == 403
    mock_db.add.assert_not_called()


def test_trusted_event_origin(mock_db):
    response = client.post(
        "/events",
        json=VALID_EVENT,
        headers={"Origin": TRUSTED_ORIGIN},
    )

    assert response.status_code == 201


def test_event_rate_limit(mock_db, monkeypatch):
    monkeypatch.setattr(
        "backend.security.MAX_EVENT_REQUESTS", 3
    )

    for _ in range(3):
        response = client.post(
            "/events",
            json=VALID_EVENT,
            headers={"Origin": TRUSTED_ORIGIN},
        )

        assert response.status_code == 201

    response = client.post(
        "/events",
        json=VALID_EVENT,
        headers={"Origin": TRUSTED_ORIGIN},
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert mock_db.add.call_count == 3

def test_oversized_event_rejected(mock_db):
    response = client.post(
        "/events",
        json={
            **VALID_EVENT,
            "event_target": "x" * 10000,
        },
        headers={"Origin": TRUSTED_ORIGIN},
    )

    assert response.status_code == 413
    mock_db.add.assert_not_called()


def test_security_headers():
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"


def test_private_response_not_cached():
    response = client.get("/analytics/summary")

    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"


def test_login_content_security_policy():
    response = client.get("/login")

    policy = response.headers["Content-Security-Policy"]

    assert "script-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy


def test_session_rate_limit(mock_db, monkeypatch):
    from backend.security import session_attempts
    from uuid import uuid4

    monkeypatch.setattr(
        "backend.security.MAX_SESSION_EVENTS", 3
    )

    session_attempts.clear()

    event = {
        **VALID_EVENT,
        "session_id": str(uuid4()),
    }

    try:
        for _ in range(3):
            response = client.post(
                "/events",
                json=event,
                headers={"Origin": TRUSTED_ORIGIN},
            )

            assert response.status_code == 201

        response = client.post(
            "/events",
            json=event,
            headers={"Origin": TRUSTED_ORIGIN},
        )

        assert response.status_code == 429

        # A different session should still be accepted.
        response = client.post(
            "/events",
            json={
                **event,
                "session_id": str(uuid4()),
            },
            headers={"Origin": TRUSTED_ORIGIN},
        )

        assert response.status_code == 201

    finally:
        session_attempts.clear()