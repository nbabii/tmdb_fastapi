from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.repositories.watch_entry_repository import WatchEntryRepository
from app.services.tmdb_service import TmdbService


async def get_watch_entry_repo(
    db: AsyncSession = Depends(get_db),
) -> WatchEntryRepository:
    return WatchEntryRepository(db)


def get_tmdb_service() -> TmdbService:
    return TmdbService()
