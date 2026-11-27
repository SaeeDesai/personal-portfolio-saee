from datetime import datetime, timedelta, timezone

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from backend.auth import (
    COOKIE_NAME,
    hash_token,
)
from backend.main import app
from backend.models import AdminSession
from backend.tests.test_integration import integration_db


ORIGIN = "http://localhost:8001"

TEST_CREDENTIALS = {
    "username": "test_admin",
    "password": "test-only-password-123",
}

TEST_PASSWORD_HASH = PasswordHasher().hash(
    TEST_CREDENTIALS["password"]
)


@pytest.fixture
def auth_client(integration_db, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "test_admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", TEST_PASSWORD_HASH)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DASHBOARD_ORIGIN", ORIGIN)

    with TestClient(app, base_url=ORIGIN) as client:
        yield client



def sign_in(client):
    return client.post(
        "/auth/login",
        json=TEST_CREDENTIALS,
        headers={"Origin": ORIGIN},
    )


def test_unauthenticated_analytics(auth_client):
    response = auth_client.get("/analytics/summary")
    assert response.status_code == 401


def test_unauthenticated_dashboard(auth_client):
    response = auth_client.get(
        "/dashboard",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_valid_login(auth_client):
    response = sign_in(auth_client)

    assert response.status_code == 200
    assert COOKIE_NAME in response.cookies

    cookie = response.headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=strict" in cookie


def test_invalid_login(auth_client):
    response = auth_client.post(
        "/auth/login",
        json={
            **TEST_CREDENTIALS,
            "password": "incorrect-password",
        },
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401
    assert COOKIE_NAME not in response.cookies


def test_authenticated_access(auth_client):
    assert sign_in(auth_client).status_code == 200

    assert auth_client.get("/dashboard").status_code == 200
    assert auth_client.get("/analytics/summary").status_code == 200
    assert auth_client.get("/auth/me").status_code == 200


def test_logout_revokes_session(auth_client):
    assert sign_in(auth_client).status_code == 200

    old_token = auth_client.cookies.get(COOKIE_NAME)

    response = auth_client.post(
        "/auth/logout",
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 200

    # Attempt to reuse the revoked session token.
    auth_client.cookies.set(COOKIE_NAME, old_token)

    assert auth_client.get("/analytics/summary").status_code == 401


def test_expired_session(auth_client, integration_db):
    assert sign_in(auth_client).status_code == 200

    token = auth_client.cookies.get(COOKIE_NAME)

    with integration_db() as db:
        session = db.get(AdminSession, hash_token(token))
        session.expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        db.commit()

    assert auth_client.get("/analytics/summary").status_code == 401


def test_untrusted_origin(auth_client):
    response = auth_client.post(
        "/auth/login",
        json=TEST_CREDENTIALS,
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403


def test_login_rate_limit(auth_client):
    for _ in range(5):
        response = auth_client.post(
            "/auth/login",
            json={
                **TEST_CREDENTIALS,
                "password": "incorrect-password",
            },
            headers={"Origin": ORIGIN},
        )

        assert response.status_code == 401

    response = sign_in(auth_client)

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_dashboard_asset_bypass(auth_client):
    response = auth_client.get("/dashboard-assets/index.html")
    assert response.status_code == 404


def test_production_cookie_security(auth_client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = sign_in(auth_client)

    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()