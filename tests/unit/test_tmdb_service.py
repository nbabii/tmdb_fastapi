import httpx
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.title import TitleType
from app.services.tmdb_service import TmdbService


@asynccontextmanager
async def client_context(client: MagicMock):
    yield client


def make_service_with_mock_client(client: MagicMock) -> TmdbService:
    return TmdbService(client_factory=lambda: client_context(client))


def make_response(*, json_data: dict, raise_error: Exception | None = None) -> MagicMock:
    response = MagicMock()
    if raise_error:
        response.raise_for_status = MagicMock(side_effect=raise_error)
    else:
        response.raise_for_status = MagicMock()
    response.json.return_value = json_data
    return response


class TestTmdbServiceSearchTitlesUnit:
    @pytest.mark.asyncio
    async def test_search_movie_returns_json(self) -> None:
        response = make_response(json_data={"results": [{"id": 550, "title": "Fight Club"}]})

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        result = await service.search_titles(query="fight club", type=TitleType.movie, page=2)

        assert result["results"][0]["id"] == 550
        client.get.assert_awaited_once_with(
            "/search/movie",
            params={"query": "fight club", "page": 2, "language": "en-US"},
        )
        response.raise_for_status.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_search_tv_with_year_adds_year_param(self) -> None:
        response = make_response(
            json_data={"results": [{"id": 1396, "title": "Breaking Bad"}]}
        )

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        result = await service.search_titles(
            query="breaking bad",
            type=TitleType.tv,
            page=1,
            year=2008,
        )

        assert result["results"][0]["id"] == 1396
        client.get.assert_awaited_once_with(
            "/search/tv",
            params={"query": "breaking bad", "page": 1, "language": "en-US", "year": 2008},
        )
        response.raise_for_status.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_search_movie_without_year_excludes_year_param(self) -> None:
        response = make_response(json_data={"results": [{"id": 550, "title": "Fight Club"}]})

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        await service.search_titles(query="fight club", type=TitleType.movie, page=1)

        client.get.assert_awaited_once_with(
            "/search/movie",
            params={"query": "fight club", "page": 1, "language": "en-US"},
        )

    @pytest.mark.asyncio
    async def test_search_titles_raises_http_error(self) -> None:
        response = make_response(
            json_data={"results": []},
            raise_error=httpx.HTTPStatusError(
                "Boom", request=MagicMock(), response=MagicMock()
            ),
        )

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        with pytest.raises(httpx.HTTPStatusError):
            await service.search_titles(query="anything", type=TitleType.movie)


class TestTmdbServiceGetMovieDetailsUnit:
    @pytest.mark.asyncio
    async def test_get_movie_details_returns_json(self) -> None:
        response = make_response(json_data={"id": 550, "title": "Fight Club"})

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        result = await service.get_movie_details(550)

        assert result["title"] == "Fight Club"
        client.get.assert_awaited_once_with("/movie/550")
        response.raise_for_status.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_get_movie_details_raises_http_error(self) -> None:
        response = make_response(
            json_data={},
            raise_error=httpx.RequestError("Network down"),
        )

        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        service = make_service_with_mock_client(client)

        with pytest.raises(httpx.RequestError):
            await service.get_movie_details(550)
