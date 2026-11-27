import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app
from backend.models import AnalyticsEvent

load_dotenv()


@pytest.fixture
def integration_db():
    url = os.environ["TEST_DATABASE_URL"]

    if make_url(url).database != "portfoliopulse_test":
        raise RuntimeError("Integration tests require the test database")

    engine = create_engine(url)
    connection = engine.connect()
    transaction = connection.begin()

    TestSession = sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    def override_get_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield TestSession
    finally:
        app.dependency_overrides.pop(get_db, None)
        transaction.rollback()
        connection.close()
        engine.dispose()


client = TestClient(app)


def test_event_persisted(integration_db):
    session_id = uuid4()

    response = client.post(
        "/events",
        json={
            "session_id": str(session_id),
            "event_type": "page_view",
            "page_path": "/personal-portfolio-saee/",
            "referrer_domain": "linkedin.com",
            "device_type": "desktop",
        },
    )

    assert response.status_code == 201

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id
            )
        )

        assert event is not None
        assert event.event_type == "page_view"
        assert event.referrer_domain == "linkedin.com"
        assert event.device_type == "desktop"
        assert event.created_at is not None


def test_invalid_event_not_persisted(integration_db):
    session_id = uuid4()

    response = client.post(
        "/events",
        json={
            "session_id": str(session_id),
            "event_type": "scroll_depth",
            "page_path": "/personal-portfolio-saee/",
            "scroll_depth": 150,
        },
    )

    assert response.status_code == 422

    with integration_db() as db:
        event = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.session_id == session_id
            )
        )

        assert event is None