import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app

FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FIXED_DATETIME = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)

VALID_PAYLOAD = {
    "tmdb_id": 550,
    "title": "Fight Club",
    "release_date": "1999-10-15",
    "runtime": 139,
    "my_rating": 9,
    "my_overview": "Great movie",
    "my_date_watched": "2026-03-28",
}


def make_mock_db(*, existing=None, scalar_error=None):
    db = AsyncMock()
    db.add = MagicMock()

    if scalar_error:
        db.scalar.side_effect = scalar_error
    else:
        db.scalar.return_value = existing

    async def mock_refresh(entry):
        entry.id = FIXED_UUID
        entry.created_at = FIXED_DATETIME

    db.refresh.side_effect = mock_refresh
    return db


def override_db(mock_db):
    async def _dep():
        yield mock_db

    app.dependency_overrides[get_db] = _dep


def clear_db_override():
    app.dependency_overrides.pop(get_db, None)


class TestCreateWatchEntry:
    def test_create_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post("/api/v1/watch-entries", json=VALID_PAYLOAD)
        finally:
            clear_db_override()

        assert response.status_code == 201
        data = response.json()
        assert data["tmdb_id"] == 550
        assert data["title"] == "Fight Club"
        assert data["my_rating"] == 9
        assert data["id"] == str(FIXED_UUID)
        assert "created_at" in data

    def test_create_minimal_payload_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries",
                json={"tmdb_id": 550, "title": "Fight Club"},
            )
        finally:
            clear_db_override()

        assert response.status_code == 201
        data = response.json()
        assert data["tmdb_id"] == 550
        assert data["my_rating"] is None
        assert data["my_overview"] is None
        assert data["my_date_watched"] is None

    def test_duplicate_tmdb_id_returns_409(self, client: TestClient) -> None:
        override_db(make_mock_db(existing=MagicMock()))
        try:
            response = client.post("/api/v1/watch-entries", json=VALID_PAYLOAD)
        finally:
            clear_db_override()

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "550" in detail
        assert "already in the database" in detail

    def test_missing_tmdb_id_returns_422(self, client: TestClient) -> None:
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "tmdb_id"}
        response = client.post("/api/v1/watch-entries", json=payload)

        assert response.status_code == 422

    def test_missing_title_returns_422(self, client: TestClient) -> None:
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "title"}
        response = client.post("/api/v1/watch-entries", json=payload)

        assert response.status_code == 422

    def test_my_rating_below_minimum_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/watch-entries", json={**VALID_PAYLOAD, "my_rating": 0}
        )

        assert response.status_code == 422

    def test_my_rating_above_maximum_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/watch-entries", json={**VALID_PAYLOAD, "my_rating": 11}
        )

        assert response.status_code == 422

    def test_my_rating_at_minimum_boundary_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries", json={**VALID_PAYLOAD, "my_rating": 1}
            )
        finally:
            clear_db_override()

        assert response.status_code == 201

    def test_my_rating_at_maximum_boundary_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries", json={**VALID_PAYLOAD, "my_rating": 10}
            )
        finally:
            clear_db_override()

        assert response.status_code == 201

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_db(make_mock_db(scalar_error=Exception("DB connection lost")))
        # raise_server_exceptions=False prevents TestClient from re-raising the
        # exception so we can inspect the HTTP response status code
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.post("/api/v1/watch-entries", json=VALID_PAYLOAD)
        finally:
            clear_db_override()

        assert response.status_code == 500
