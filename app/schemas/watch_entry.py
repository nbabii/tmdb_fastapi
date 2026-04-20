import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchEntryCreate(BaseModel):
    tmdb_id: int
    title: str
    release_date: date | None = None
    my_rating: int | None = Field(default=None, ge=1, le=10)
    my_overview: str | None = None
    my_date_watched: date | None = None


class WatchEntryResponse(WatchEntryCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WatchEntrySkipped(BaseModel):
    tmdb_id: int
    title: str
    reason: str


class WatchEntryBulkResult(BaseModel):
    created: list[WatchEntryResponse]
    skipped: list[WatchEntrySkipped]


class WatchEntryListItem(BaseModel):
    id: uuid.UUID
    tmdb_id: int
    title: str
    release_date: date | None = None
    my_rating: int | None = None
    my_overview: str | None = None
    my_date_watched: date | None = None

    model_config = ConfigDict(from_attributes=True)


class WatchEntryListResponse(BaseModel):
    items: list[WatchEntryListItem]
    total: int
    limit: int
    offset: int


class WatchEntryDetailResponse(BaseModel):
    id: uuid.UUID
    tmdb_id: int
    title: str
    overview: str | None = None
    release_date: date | None = None
    runtime: int | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    my_rating: int | None = None
    my_overview: str | None = None
    my_date_watched: date | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
