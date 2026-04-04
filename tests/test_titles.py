from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.api.deps import get_tmdb_service
from app.main import app
from app.services.tmdb_service import TmdbService
from tests.conftest import MOCK_MOVIE_RESPONSE, MOCK_TV_RESPONSE


def make_mock_tmdb(*, search_return=None, search_error=None):
    mock = MagicMock(spec=TmdbService)
    if search_error:
        mock.search_titles = AsyncMock(side_effect=search_error)
    else:
        mock.search_titles = AsyncMock(return_value=search_return)
    return mock


def override_tmdb(mock):
    app.dependency_overrides[get_tmdb_service] = lambda: mock


def clear_tmdb_override():
    app.dependency_overrides.pop(get_tmdb_service, None)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSearchTitlesEndpoint:
    def test_search_movie_returns_200(self, client: TestClient) -> None:
        override_tmdb(make_mock_tmdb(search_return=MOCK_MOVIE_RESPONSE))
        try:
            response = client.get("/api/v1/titles/search?query=fight+club&type=movie")
        finally:
            clear_tmdb_override()

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["total_results"] == 1
        assert data["results"][0]["title"] == "Fight Club"

    def test_search_tv_returns_200(self, client: TestClient) -> None:
        override_tmdb(make_mock_tmdb(search_return=MOCK_TV_RESPONSE))
        try:
            response = client.get("/api/v1/titles/search?query=breaking+bad&type=tv")
        finally:
            clear_tmdb_override()

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["title"] == "Breaking Bad"

    def test_search_with_year_param(self, client: TestClient) -> None:
        mock = make_mock_tmdb(search_return=MOCK_MOVIE_RESPONSE)
        override_tmdb(mock)
        try:
            client.get("/api/v1/titles/search?query=fight+club&type=movie&year=1999")
        finally:
            clear_tmdb_override()

        mock.search_titles.assert_called_once_with(
            query="fight club", type="movie", page=1, year=1999
        )

    def test_search_with_page_param(self, client: TestClient) -> None:
        mock = make_mock_tmdb(search_return=MOCK_MOVIE_RESPONSE)
        override_tmdb(mock)
        try:
            client.get("/api/v1/titles/search?query=fight+club&type=movie&page=2")
        finally:
            clear_tmdb_override()

        mock.search_titles.assert_called_once_with(
            query="fight club", type="movie", page=2, year=None
        )

    def test_missing_query_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/titles/search?type=movie")

        assert response.status_code == 422

    def test_missing_type_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/titles/search?query=inception")

        assert response.status_code == 422

    def test_invalid_type_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/titles/search?query=inception&type=cartoon")

        assert response.status_code == 422

    def test_empty_query_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/titles/search?query=&type=movie")

        assert response.status_code == 422

    def test_page_out_of_range_returns_422(self, client: TestClient) -> None:
        response = client.get("/api/v1/titles/search?query=inception&type=movie&page=501")

        assert response.status_code == 422

    def test_tmdb_error_returns_502(self, client: TestClient) -> None:
        override_tmdb(make_mock_tmdb(search_error=Exception("TMDB is down")))
        try:
            response = client.get("/api/v1/titles/search?query=inception&type=movie")
        finally:
            clear_tmdb_override()

        assert response.status_code == 502
        assert response.json()["detail"] == "An unexpected error occurred."
