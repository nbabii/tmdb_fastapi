import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app

FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FIXED_DATETIME = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)

VALID_PAYLOAD = {
    "tmdb_id": 550,
    "title": "Fight Club",
    "release_date": "1999-10-15",
    "my_rating": 9,
    "my_overview": "Great movie",
    "my_date_watched": "2026-03-28",
}


def make_mock_db(*, existing=None, existing_tmdb_ids=None, scalar_error=None):
    db = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()

    if scalar_error:
        # apply to both scalar (GET) and scalars (POST bulk check)
        db.scalar.side_effect = scalar_error
        db.scalars.side_effect = scalar_error
    else:
        # GET: single-row lookup
        db.scalar.return_value = existing
        # POST: bulk tmdb_id existence check — scalars().all() returns a list of ints
        scalars_result = MagicMock()
        scalars_result.all.return_value = list(existing_tmdb_ids or [])
        db.scalars.return_value = scalars_result

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
    def test_create_single_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_db_override()

        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 1
        assert data["skipped"] == []
        entry = data["created"][0]
        assert entry["tmdb_id"] == 550
        assert entry["title"] == "Fight Club"
        assert entry["my_rating"] == 9
        assert entry["id"] == str(FIXED_UUID)
        assert "created_at" in entry

    def test_create_multiple_returns_201(self, client: TestClient) -> None:
        payload = [VALID_PAYLOAD, {**VALID_PAYLOAD, "tmdb_id": 999, "title": "Se7en"}]
        override_db(make_mock_db())
        try:
            response = client.post("/api/v1/watch-entries", json=payload)
        finally:
            clear_db_override()

        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 2
        assert data["skipped"] == []

    def test_create_minimal_payload_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries",
                json=[{"tmdb_id": 550, "title": "Fight Club"}],
            )
        finally:
            clear_db_override()

        assert response.status_code == 201
        entry = response.json()["created"][0]
        assert entry["tmdb_id"] == 550
        assert entry["my_rating"] is None
        assert entry["my_overview"] is None
        assert entry["my_date_watched"] is None

    def test_all_duplicates_returns_409(self, client: TestClient) -> None:
        override_db(make_mock_db(existing_tmdb_ids=[550]))
        try:
            response = client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_db_override()

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert detail[0]["tmdb_id"] == 550
        assert "already in the database" in detail[0]["reason"]

    def test_partial_duplicate_returns_207(self, client: TestClient) -> None:
        payload = [VALID_PAYLOAD, {**VALID_PAYLOAD, "tmdb_id": 999, "title": "Se7en"}]
        override_db(make_mock_db(existing_tmdb_ids=[550]))
        try:
            response = client.post("/api/v1/watch-entries", json=payload)
        finally:
            clear_db_override()

        assert response.status_code == 207
        data = response.json()
        assert len(data["created"]) == 1
        assert data["created"][0]["tmdb_id"] == 999
        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["tmdb_id"] == 550

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post("/api/v1/watch-entries", json=[])
        finally:
            clear_db_override()

        assert response.status_code == 422

    def test_missing_tmdb_id_returns_422(self, client: TestClient) -> None:
        payload = [{k: v for k, v in VALID_PAYLOAD.items() if k != "tmdb_id"}]
        response = client.post("/api/v1/watch-entries", json=payload)

        assert response.status_code == 422

    def test_missing_title_returns_422(self, client: TestClient) -> None:
        payload = [{k: v for k, v in VALID_PAYLOAD.items() if k != "title"}]
        response = client.post("/api/v1/watch-entries", json=payload)

        assert response.status_code == 422

    def test_my_rating_below_minimum_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 0}]
        )

        assert response.status_code == 422

    def test_my_rating_above_maximum_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 11}]
        )

        assert response.status_code == 422

    def test_my_rating_at_minimum_boundary_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 1}]
            )
        finally:
            clear_db_override()

        assert response.status_code == 201

    def test_my_rating_at_maximum_boundary_returns_201(self, client: TestClient) -> None:
        override_db(make_mock_db())
        try:
            response = client.post(
                "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 10}]
            )
        finally:
            clear_db_override()

        assert response.status_code == 201

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_db(make_mock_db(scalar_error=Exception("DB connection lost")))
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_db_override()

        assert response.status_code == 500


MOCK_TMDB_DETAILS = {
    "id": 550,
    "title": "Fight Club",
    "overview": "An insomniac office worker forms an underground fight club.",
    "runtime": 139,
    "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    "vote_average": 8.4,
}


def make_mock_entry(**overrides) -> MagicMock:
    attrs = {
        "id": FIXED_UUID,
        "tmdb_id": 550,
        "title": "Fight Club",
        "release_date": date(1999, 10, 15),
        "my_rating": 9,
        "my_overview": "Great movie",
        "my_date_watched": date(2026, 3, 28),
        "created_at": FIXED_DATETIME,
        **overrides,
    }
    entry = MagicMock()
    for key, value in attrs.items():
        setattr(entry, key, value)
    col_mocks = []
    for key in attrs:
        col = MagicMock()
        col.key = key
        col_mocks.append(col)
    entry.__table__ = MagicMock()
    entry.__table__.columns = col_mocks
    return entry


class TestGetWatchEntry:
    def test_get_by_id_returns_200(self, client: TestClient) -> None:
        entry = make_mock_entry()
        override_db(make_mock_db(existing=entry))
        try:
            with patch(
                "app.services.tmdb_client.tmdb_client.get_movie_details",
                new=AsyncMock(return_value=MOCK_TMDB_DETAILS),
            ):
                response = client.get(f"/api/v1/watch-entries?id={FIXED_UUID}")
        finally:
            clear_db_override()

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(FIXED_UUID)
        assert data["tmdb_id"] == 550
        assert data["title"] == "Fight Club"
        assert data["overview"] == MOCK_TMDB_DETAILS["overview"]
        assert data["runtime"] == MOCK_TMDB_DETAILS["runtime"]
        assert data["poster_path"] == MOCK_TMDB_DETAILS["poster_path"]
        assert data["vote_average"] == MOCK_TMDB_DETAILS["vote_average"]
        assert data["my_rating"] == 9
        assert data["release_date"] == "1999-10-15"

    def test_get_by_tmdb_id_returns_200(self, client: TestClient) -> None:
        entry = make_mock_entry()
        override_db(make_mock_db(existing=entry))
        try:
            with patch(
                "app.services.tmdb_client.tmdb_client.get_movie_details",
                new=AsyncMock(return_value=MOCK_TMDB_DETAILS),
            ):
                response = client.get("/api/v1/watch-entries?tmdb_id=550")
        finally:
            clear_db_override()

        assert response.status_code == 200
        assert response.json()["tmdb_id"] == 550

    def test_id_takes_precedence_over_tmdb_id(self, client: TestClient) -> None:
        entry = make_mock_entry()
        mock_db = make_mock_db(existing=entry)
        override_db(mock_db)
        try:
            with patch(
                "app.services.tmdb_client.tmdb_client.get_movie_details",
                new=AsyncMock(return_value=MOCK_TMDB_DETAILS),
            ):
                response = client.get(f"/api/v1/watch-entries?id={FIXED_UUID}&tmdb_id=550")
        finally:
            clear_db_override()

        assert response.status_code == 200
        # scalar should have been called with the id-based query (called once)
        mock_db.scalar.assert_called_once()

    def test_no_params_returns_400(self, client: TestClient) -> None:
        response = client.get("/api/v1/watch-entries")

        assert response.status_code == 400
        assert "id" in response.json()["detail"] or "tmdb_id" in response.json()["detail"]

    def test_entry_not_found_returns_404(self, client: TestClient) -> None:
        override_db(make_mock_db(existing=None))
        try:
            response = client.get(f"/api/v1/watch-entries?id={FIXED_UUID}")
        finally:
            clear_db_override()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_tmdb_api_error_returns_502(self, client: TestClient) -> None:
        entry = make_mock_entry()
        override_db(make_mock_db(existing=entry))
        try:
            with patch(
                "app.services.tmdb_client.tmdb_client.get_movie_details",
                new=AsyncMock(side_effect=httpx.HTTPError("TMDB is down")),
            ):
                response = client.get(f"/api/v1/watch-entries?id={FIXED_UUID}")
        finally:
            clear_db_override()

        assert response.status_code == 502
        assert "TMDB API error" in response.json()["detail"]

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_db(make_mock_db(scalar_error=Exception("DB connection lost")))
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.get(f"/api/v1/watch-entries?id={FIXED_UUID}")
        finally:
            clear_db_override()

        assert response.status_code == 500
