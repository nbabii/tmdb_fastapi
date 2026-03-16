from enum import Enum

from pydantic import BaseModel


class TitleType(str, Enum):
    movie = "movie"
    tv = "tv"


class TitleResult(BaseModel):
    id: int
    title: str
    original_title: str
    overview: str
    release_date: str | None = None
    poster_path: str | None = None
    backdrop_path: str | None = None
    popularity: float
    vote_average: float
    vote_count: int
    genre_ids: list[int] = []
    original_language: str
    adult: bool
    video: bool


class TitleSearchResponse(BaseModel):
    page: int
    results: list[TitleResult]
    total_pages: int
    total_results: int
