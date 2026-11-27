from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.database import get_db
from backend.main import app


VALID_EVENT = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "page_view",
    "page_path": "/personal-portfolio-saee/",
}


@pytest.fixture
def mock_db():
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    yield db

    app.dependency_overrides.pop(get_db, None)


client = TestClient(
    app,
    headers={"Origin": "https://saeedesai.github.io"},
)


def test_create_event(mock_db):
    response = client.post("/events", json=VALID_EVENT)

    assert response.status_code == 201
    assert response.json() == {"status": "accepted"}

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_invalid_event(mock_db):
    response = client.post(
        "/events",
        json={**VALID_EVENT, "event_type": "invalid"},
    )

    assert response.status_code == 422

    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()


def test_database_failure(mock_db):
    mock_db.commit.side_effect = SQLAlchemyError("Simulated failure")

    response = client.post("/events", json=VALID_EVENT)

    assert response.status_code == 503
    mock_db.rollback.assert_called_once()