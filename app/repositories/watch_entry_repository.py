import uuid

from sqlalchemy import func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watched_movie import WatchedMovie


class WatchEntryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_existing_tmdb_ids(self, tmdb_ids: list[int]) -> set[int]:
        rows = await self._db.scalars(
            select(WatchedMovie.tmdb_id).where(WatchedMovie.tmdb_id.in_(tmdb_ids))
        )
        return set(rows.all())

    async def find_by_id(self, entry_id: uuid.UUID) -> WatchedMovie | None:
        return await self._db.scalar(
            select(WatchedMovie).where(WatchedMovie.id == entry_id)
        )

    async def find_by_tmdb_id(self, tmdb_id: int) -> WatchedMovie | None:
        return await self._db.scalar(
            select(WatchedMovie).where(WatchedMovie.tmdb_id == tmdb_id)
        )

    async def bulk_create(self, entries: list[WatchedMovie]) -> list[WatchedMovie]:
        self._db.add_all(entries)
        await self._db.commit()
        for entry in entries:
            await self._db.refresh(entry)
        return entries

    async def count_all(self) -> int:
        result = await self._db.scalar(select(func.count()).select_from(WatchedMovie))
        return result or 0

    async def list_all(self, limit: int = 10, offset: int = 0) -> list[WatchedMovie]:
        rows = await self._db.scalars(
            select(WatchedMovie)
            .order_by(nullslast(WatchedMovie.my_date_watched.desc()))
            .limit(limit)
            .offset(offset)
        )
        return list(rows.all())
