import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.deps import get_tmdb_service, get_watch_entry_repo
from app.models.watched_movie import WatchedMovie
from app.repositories.watch_entry_repository import WatchEntryRepository
from app.schemas.watch_entry import (
    WatchEntryBulkResult,
    WatchEntryCreate,
    WatchEntryDetailResponse,
    WatchEntryResponse,
    WatchEntrySkipped,
)
from app.services.tmdb_service import TmdbService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=WatchEntryBulkResult)
async def create_watch_entries(
    body: list[WatchEntryCreate],
    repo: WatchEntryRepository = Depends(get_watch_entry_repo),
) -> JSONResponse:
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must not be empty.")

    existing_ids = await repo.find_existing_tmdb_ids([item.tmdb_id for item in body])

    to_create: list[WatchedMovie] = []
    skipped: list[WatchEntrySkipped] = []

    for item in body:
        if item.tmdb_id in existing_ids:
            logger.warning("Duplicate tmdb_id=%d skipped", item.tmdb_id)
            skipped.append(
                WatchEntrySkipped(
                    tmdb_id=item.tmdb_id,
                    title=item.title,
                    reason=f"Movie with tmdb_id {item.tmdb_id} and title '{item.title}' is already in the database.",
                )
            )
        else:
            to_create.append(WatchedMovie(**item.model_dump()))

    if not to_create and skipped:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=[s.model_dump() for s in skipped],
        )

    created = await repo.bulk_create(to_create)
    for entry in created:
        logger.info("Watch entry created: tmdb_id=%d id=%s", entry.tmdb_id, entry.id)

    result = WatchEntryBulkResult(
        created=[WatchEntryResponse.model_validate(e) for e in created],
        skipped=skipped,
    )

    http_status = status.HTTP_201_CREATED if not skipped else status.HTTP_207_MULTI_STATUS
    return JSONResponse(content=result.model_dump(mode="json"), status_code=http_status)


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
