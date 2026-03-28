import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.watched_movie import WatchedMovie
from app.schemas.watch_entry import WatchEntryCreate, WatchEntryResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=WatchEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_watch_entry(
    body: WatchEntryCreate,
    db: AsyncSession = Depends(get_db),
) -> WatchEntryResponse:
    existing = await db.scalar(
        select(WatchedMovie).where(WatchedMovie.tmdb_id == body.tmdb_id)
    )
    if existing:
        logger.warning("Duplicate tmdb_id=%d rejected", body.tmdb_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Movie with tmdb_id {body.tmdb_id} is already in the database.",
        )
    entry = WatchedMovie(**body.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Watch entry created: tmdb_id=%d id=%s", entry.tmdb_id, entry.id)
    return entry
