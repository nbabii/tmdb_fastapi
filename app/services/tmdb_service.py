import httpx
from collections.abc import Callable

from app.schemas.title import TitleType

ClientFactory = Callable[[], httpx.AsyncClient]


class TmdbService:
    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory

    async def search_titles(
        self,
        query: str,
        type: TitleType,
        page: int = 1,
        year: int | None = None,
    ) -> dict:
        params: dict = {
            "query": query,
            "page": page,
            "language": "en-US",
        }

        if year:
            params["year"] = year

        path = "/search/movie" if type == TitleType.movie else "/search/tv"

        async with self._client_factory() as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    async def get_movie_details(self, movie_id: int) -> dict:
        async with self._client_factory() as client:
            response = await client.get(f"/movie/{movie_id}")
            response.raise_for_status()
            return response.json()
