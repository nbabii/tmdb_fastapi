from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.conftest import MOCK_MOVIE_RESPONSE, MOCK_TV_RESPONSE


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestSearchTitlesEndpoint:
    def test_search_movie_returns_200(self, client: TestClient) -> None:
        with patch(
            "app.services.tmdb_client.tmdb_client.search_titles",
            new=AsyncMock(return_value=MOCK_MOVIE_RESPONSE),
        ):
            response = client.get("/api/v1/titles/search?query=fight+club&type=movie")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["total_results"] == 1
        assert data["results"][0]["title"] == "Fight Club"

    def test_search_tv_returns_200(self, client: TestClient) -> None:
        with patch(
            "app.services.tmdb_client.tmdb_client.search_titles",
            new=AsyncMock(return_value=MOCK_TV_RESPONSE),
        ):
            response = client.get("/api/v1/titles/search?query=breaking+bad&type=tv")

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["title"] == "Breaking Bad"

    def test_search_with_year_param(self, client: TestClient) -> None:
        with patch(
            "app.services.tmdb_client.tmdb_client.search_titles",
            new=AsyncMock(return_value=MOCK_MOVIE_RESPONSE),
        ) as mock:
            client.get("/api/v1/titles/search?query=fight+club&type=movie&year=1999")

        mock.assert_called_once_with(
            query="fight club", type="movie", page=1, year=1999
        )

    def test_search_with_page_param(self, client: TestClient) -> None:
        with patch(
            "app.services.tmdb_client.tmdb_client.search_titles",
            new=AsyncMock(return_value=MOCK_MOVIE_RESPONSE),
        ) as mock:
            client.get("/api/v1/titles/search?query=fight+club&type=movie&page=2")

        mock.assert_called_once_with(
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
        with patch(
            "app.services.tmdb_client.tmdb_client.search_titles",
            new=AsyncMock(side_effect=Exception("TMDB is down")),
        ):
            response = client.get("/api/v1/titles/search?query=inception&type=movie")

        assert response.status_code == 502
        assert "TMDB API error" in response.json()["detail"]
