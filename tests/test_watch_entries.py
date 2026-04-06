import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
from fastapi.testclient import TestClient

from app.api.deps import get_tmdb_service, get_watch_entry_repo
from app.main import app
from app.repositories.watch_entry_repository import WatchEntryRepository
from app.services.tmdb_service import TmdbService

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


def make_mock_repo(*, existing=None, existing_tmdb_ids=None, error=None):
    repo = MagicMock(spec=WatchEntryRepository)

    if error:
        repo.find_existing_tmdb_ids = AsyncMock(side_effect=error)
        repo.find_by_id = AsyncMock(side_effect=error)
        repo.find_by_tmdb_id = AsyncMock(side_effect=error)
        repo.list_all = AsyncMock(side_effect=error)
    else:
        repo.find_existing_tmdb_ids = AsyncMock(return_value=set(existing_tmdb_ids or []))
        repo.find_by_id = AsyncMock(return_value=existing)
        repo.find_by_tmdb_id = AsyncMock(return_value=existing)
        repo.list_all = AsyncMock(return_value=[])

    async def _bulk_create(entries):
        for entry in entries:
            entry.id = FIXED_UUID
            entry.created_at = FIXED_DATETIME
        return entries

    repo.bulk_create = AsyncMock(side_effect=_bulk_create)
    return repo


def override_repo(mock_repo):
    app.dependency_overrides[get_watch_entry_repo] = lambda: mock_repo


def clear_repo_override():
    app.dependency_overrides.pop(get_watch_entry_repo, None)


def make_mock_tmdb(*, details_return=None, details_error=None):
    mock = MagicMock(spec=TmdbService)
    if details_error:
        mock.get_movie_details = AsyncMock(side_effect=details_error)
    else:
        mock.get_movie_details = AsyncMock(return_value=details_return)
    return mock


def override_tmdb(mock):
    app.dependency_overrides[get_tmdb_service] = lambda: mock


def clear_tmdb_override():
    app.dependency_overrides.pop(get_tmdb_service, None)


class TestCreateWatchEntry:
    def test_create_single_returns_201(self, client: TestClient) -> None:
        override_repo(make_mock_repo())
        try:
            response = client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_repo_override()

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
        override_repo(make_mock_repo())
        try:
            response = client.post("/api/v1/watch-entries", json=payload)
        finally:
            clear_repo_override()

        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 2
        assert data["skipped"] == []

    def test_create_minimal_payload_returns_201(self, client: TestClient) -> None:
        override_repo(make_mock_repo())
        try:
            response = client.post(
                "/api/v1/watch-entries",
                json=[{"tmdb_id": 550, "title": "Fight Club"}],
            )
        finally:
            clear_repo_override()

        assert response.status_code == 201
        entry = response.json()["created"][0]
        assert entry["tmdb_id"] == 550
        assert entry["my_rating"] is None
        assert entry["my_overview"] is None
        assert entry["my_date_watched"] is None

    def test_all_duplicates_returns_409(self, client: TestClient) -> None:
        override_repo(make_mock_repo(existing_tmdb_ids=[550]))
        try:
            response = client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_repo_override()

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert detail[0]["tmdb_id"] == 550
        assert "already in the database" in detail[0]["reason"]

    def test_partial_duplicate_returns_207(self, client: TestClient) -> None:
        payload = [VALID_PAYLOAD, {**VALID_PAYLOAD, "tmdb_id": 999, "title": "Se7en"}]
        override_repo(make_mock_repo(existing_tmdb_ids=[550]))
        try:
            response = client.post("/api/v1/watch-entries", json=payload)
        finally:
            clear_repo_override()

        assert response.status_code == 207
        data = response.json()
        assert len(data["created"]) == 1
        assert data["created"][0]["tmdb_id"] == 999
        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["tmdb_id"] == 550

    def test_empty_body_returns_422(self, client: TestClient) -> None:
        override_repo(make_mock_repo())
        try:
            response = client.post("/api/v1/watch-entries", json=[])
        finally:
            clear_repo_override()

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
        override_repo(make_mock_repo())
        try:
            response = client.post(
                "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 1}]
            )
        finally:
            clear_repo_override()

        assert response.status_code == 201

    def test_my_rating_at_maximum_boundary_returns_201(self, client: TestClient) -> None:
        override_repo(make_mock_repo())
        try:
            response = client.post(
                "/api/v1/watch-entries", json=[{**VALID_PAYLOAD, "my_rating": 10}]
            )
        finally:
            clear_repo_override()

        assert response.status_code == 201

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_repo(make_mock_repo(error=Exception("DB connection lost")))
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.post("/api/v1/watch-entries", json=[VALID_PAYLOAD])
        finally:
            clear_repo_override()

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
        override_repo(make_mock_repo(existing=entry))
        override_tmdb(make_mock_tmdb(details_return=MOCK_TMDB_DETAILS))
        try:
            response = client.get(f"/api/v1/watch-entry?id={FIXED_UUID}")
        finally:
            clear_repo_override()
            clear_tmdb_override()

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
        override_repo(make_mock_repo(existing=entry))
        override_tmdb(make_mock_tmdb(details_return=MOCK_TMDB_DETAILS))
        try:
            response = client.get("/api/v1/watch-entry?tmdb_id=550")
        finally:
            clear_repo_override()
            clear_tmdb_override()

        assert response.status_code == 200
        assert response.json()["tmdb_id"] == 550

    def test_id_takes_precedence_over_tmdb_id(self, client: TestClient) -> None:
        entry = make_mock_entry()
        mock_repo = make_mock_repo(existing=entry)
        override_repo(mock_repo)
        override_tmdb(make_mock_tmdb(details_return=MOCK_TMDB_DETAILS))
        try:
            response = client.get(f"/api/v1/watch-entry?id={FIXED_UUID}&tmdb_id=550")
        finally:
            clear_repo_override()
            clear_tmdb_override()

        assert response.status_code == 200
        mock_repo.find_by_id.assert_called_once()

    def test_no_params_returns_400(self, client: TestClient) -> None:
        response = client.get("/api/v1/watch-entry")

        assert response.status_code == 400
        assert "id" in response.json()["detail"] or "tmdb_id" in response.json()["detail"]

    def test_entry_not_found_returns_404(self, client: TestClient) -> None:
        override_repo(make_mock_repo(existing=None))
        try:
            response = client.get(f"/api/v1/watch-entry?id={FIXED_UUID}")
        finally:
            clear_repo_override()

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_tmdb_api_error_returns_502(self, client: TestClient) -> None:
        entry = make_mock_entry()
        override_repo(make_mock_repo(existing=entry))
        override_tmdb(make_mock_tmdb(details_error=httpx.HTTPError("TMDB is down")))
        try:
            response = client.get(f"/api/v1/watch-entry?id={FIXED_UUID}")
        finally:
            clear_repo_override()
            clear_tmdb_override()

        assert response.status_code == 502
        assert response.json()["detail"] == "An unexpected error occurred."

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_repo(make_mock_repo(error=Exception("DB connection lost")))
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.get(f"/api/v1/watch-entry?id={FIXED_UUID}")
        finally:
            clear_repo_override()

        assert response.status_code == 500


class TestListWatchEntries:
    def test_empty_db_returns_200_with_empty_list(self, client: TestClient) -> None:
        override_repo(make_mock_repo())
        try:
            response = client.get("/api/v1/watch-entries")
        finally:
            clear_repo_override()

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_entries_with_correct_fields(self, client: TestClient) -> None:
        entry = make_mock_entry()
        mock_repo = make_mock_repo()
        mock_repo.list_all = AsyncMock(return_value=[entry])
        override_repo(mock_repo)
        try:
            response = client.get("/api/v1/watch-entries")
        finally:
            clear_repo_override()

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == str(FIXED_UUID)
        assert item["tmdb_id"] == 550
        assert item["title"] == "Fight Club"
        assert item["my_rating"] == 9
        assert item["release_date"] == "1999-10-15"
        assert item["my_date_watched"] == "2026-03-28"
        assert "created_at" not in item

    def test_limit_param_is_respected(self, client: TestClient) -> None:
        entries = [make_mock_entry(tmdb_id=i, title=f"Movie {i}") for i in range(3)]
        mock_repo = make_mock_repo()
        mock_repo.list_all = AsyncMock(return_value=[entries[0]])
        override_repo(mock_repo)
        try:
            response = client.get("/api/v1/watch-entries?limit=1")
        finally:
            clear_repo_override()

        assert response.status_code == 200
        assert response.json()["total"] == 1
        mock_repo.list_all.assert_called_once_with(limit=1)

    def test_limit_zero_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/watch-entries?limit=0")

        assert response.status_code == 422

    def test_limit_above_max_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/watch-entries?limit=101")

        assert response.status_code == 422

    def test_default_limit_is_10(self, client: TestClient) -> None:
        mock_repo = make_mock_repo()
        override_repo(mock_repo)
        try:
            client.get("/api/v1/watch-entries")
        finally:
            clear_repo_override()

        mock_repo.list_all.assert_called_once_with(limit=10)

    def test_db_error_returns_500(self, client: TestClient) -> None:
        override_repo(make_mock_repo(error=Exception("DB connection lost")))
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        try:
            response = no_raise_client.get("/api/v1/watch-entries")
        finally:
            clear_repo_override()

        assert response.status_code == 500
