import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import get_watch_entry_repo
from app.models.watched_movie import WatchedMovie
from app.repositories.watch_entry_repository import WatchEntryRepository
from app.schemas.watch_entry import (
    WatchEntryBulkResult,
    WatchEntryCreate,
    WatchEntryListItem,
    WatchEntryListResponse,
    WatchEntryResponse,
    WatchEntrySkipped,
)

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


@router.get("", response_model=WatchEntryListResponse)
async def list_watch_entries(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repo: WatchEntryRepository = Depends(get_watch_entry_repo),
) -> WatchEntryListResponse:
    total, entries = (
        await repo.count_all(),
        await repo.list_all(limit=limit, offset=offset),
    )
    logger.info("Watch entries listed: count=%d limit=%d offset=%d total=%d", len(entries), limit, offset, total)
    return WatchEntryListResponse(
        items=[WatchEntryListItem.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )
