import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.watched_movie import WatchedMovie
from app.schemas.watch_entry import WatchEntryCreate, WatchEntryDetailResponse, WatchEntryResponse
from app.services.tmdb_client import tmdb_client

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
            detail=f"Movie with tmdb_id {body.tmdb_id} and name '{body.title}' is already in the database.",
        )
    entry = WatchedMovie(**body.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info("Watch entry created: tmdb_id=%d id=%s", entry.tmdb_id, entry.id)
    return entry


@router.get("", response_model=WatchEntryDetailResponse)
async def get_watch_entry(
    id: uuid.UUID | None = None,
    tmdb_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> WatchEntryDetailResponse:
    if id is None and tmdb_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide 'id' or 'tmdb_id'.")

    if id is not None:
        entry = await db.scalar(select(WatchedMovie).where(WatchedMovie.id == id))
    else:
        entry = await db.scalar(select(WatchedMovie).where(WatchedMovie.tmdb_id == tmdb_id))

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watch entry not found.")

    try:
        tmdb_data = await tmdb_client.get_movie_details(entry.tmdb_id)
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
