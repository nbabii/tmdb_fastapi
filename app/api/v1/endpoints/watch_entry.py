import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_tmdb_service, get_watch_entry_repo
from app.repositories.watch_entry_repository import WatchEntryRepository
from app.schemas.watch_entry import WatchEntryDetailResponse
from app.services.tmdb_service import TmdbService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=WatchEntryDetailResponse)
async def get_watch_entry(
    id: uuid.UUID | None = None,
    tmdb_id: int | None = None,
    repo: WatchEntryRepository = Depends(get_watch_entry_repo),
    tmdb: TmdbService = Depends(get_tmdb_service),
) -> WatchEntryDetailResponse:
    if id is None and tmdb_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide 'id' or 'tmdb_id'.")

    if id is not None:
        entry = await repo.find_by_id(id)
    else:
        entry = await repo.find_by_tmdb_id(tmdb_id)

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch entry not found.")

    try:
        tmdb_data = await tmdb.get_movie_details(entry.tmdb_id)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB API error: {exc}")

    logger.info("Watch entry fetched: tmdb_id=%d id=%s", entry.tmdb_id, entry.id)
    return WatchEntryDetailResponse(
        **{c.key: getattr(entry, c.key) for c in entry.__table__.columns},
        overview=tmdb_data.get("overview"),
        runtime=tmdb_data.get("runtime"),
        poster_path=tmdb_data.get("poster_path"),
        vote_average=tmdb_data.get("vote_average"),
    )
