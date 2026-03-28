import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchEntryCreate(BaseModel):
    tmdb_id: int
    title: str
    release_date: date | None = None
    runtime: int | None = None
    my_rating: int | None = Field(default=None, ge=1, le=10)
    my_overview: str | None = None
    my_date_watched: date | None = None


class WatchEntryResponse(WatchEntryCreate):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
