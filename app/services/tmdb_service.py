import httpx

from app.core.config import settings
from app.schemas.title import TitleType


class TmdbService:
    def __init__(self) -> None:
        self._base_url = settings.TMDB_BASE_URL
        self._headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {settings.TMDB_API_KEY}",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, headers=self._headers)

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

        async with self._client() as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    async def get_movie_details(self, movie_id: int) -> dict:
        async with self._client() as client:
            response = await client.get(f"/movie/{movie_id}")
            response.raise_for_status()
            return response.json()
