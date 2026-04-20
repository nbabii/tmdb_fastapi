import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.watch_entry_repository import WatchEntryRepository
from app.schemas.watch_entry import SortOrder, WatchEntrySortBy

FIXED_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FIXED_DATETIME = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)


class TestWatchEntryRepositoryUnit:
    @pytest.mark.asyncio
    async def test_find_existing_tmdb_ids_returns_set(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = [550, 999]
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        result = await repo.find_existing_tmdb_ids([550, 999, 123])

        assert result == {550, 999}
        db.scalars.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_id_returns_entry(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        entry = MagicMock(id=FIXED_UUID, tmdb_id=550, created_at=FIXED_DATETIME)
        db.scalar.return_value = entry
        repo = WatchEntryRepository(db)

        result = await repo.find_by_id(FIXED_UUID)

        assert result is entry
        db.scalar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_by_tmdb_id_returns_entry(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        entry = MagicMock(id=FIXED_UUID, tmdb_id=550, created_at=FIXED_DATETIME)
        db.scalar.return_value = entry
        repo = WatchEntryRepository(db)

        result = await repo.find_by_tmdb_id(550)

        assert result is entry
        db.scalar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_create_calls_commit_and_refresh(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        repo = WatchEntryRepository(db)
        entry1 = MagicMock(id=FIXED_UUID, tmdb_id=550, created_at=FIXED_DATETIME)
        entry2 = MagicMock(id=FIXED_UUID, tmdb_id=999, created_at=FIXED_DATETIME)
        entries = [entry1, entry2]

        result = await repo.bulk_create(entries)

        assert result == entries
        db.add_all.assert_called_once_with(entries)
        db.commit.assert_awaited_once()
        assert db.refresh.await_count == 2
        db.refresh.assert_any_await(entry1)
        db.refresh.assert_any_await(entry2)

    @pytest.mark.asyncio
    async def test_list_all_returns_limited_rows(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        row1 = MagicMock(tmdb_id=550, created_at=FIXED_DATETIME)
        row2 = MagicMock(tmdb_id=999, created_at=FIXED_DATETIME)
        rows = MagicMock()
        rows.all.return_value = [row1, row2]
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        result = await repo.list_all(limit=2)

        assert result == [row1, row2]
        db.scalars.assert_awaited_once()
        statement = db.scalars.await_args.args[0]
        assert "LIMIT" in str(statement)

    @pytest.mark.asyncio
    async def test_list_all_applies_offset(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = []
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        await repo.list_all(limit=5, offset=20)

        statement = db.scalars.await_args.args[0]
        assert "OFFSET" in str(statement)

    @pytest.mark.asyncio
    async def test_list_all_default_sort_uses_my_rating(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = []
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        await repo.list_all()

        statement = db.scalars.await_args.args[0]
        assert "my_rating" in str(statement)

    @pytest.mark.asyncio
    async def test_list_all_sort_by_my_date_watched_contains_column(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = []
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        await repo.list_all(sort_by=WatchEntrySortBy.my_date_watched)

        statement = db.scalars.await_args.args[0]
        assert "my_date_watched" in str(statement)

    @pytest.mark.asyncio
    async def test_list_all_sort_order_asc_contains_asc(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = []
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        await repo.list_all(sort_order=SortOrder.asc)

        statement = db.scalars.await_args.args[0]
        assert "ASC" in str(statement)

    @pytest.mark.asyncio
    async def test_list_all_sort_order_desc_contains_desc(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        rows = MagicMock()
        rows.all.return_value = []
        db.scalars.return_value = rows
        repo = WatchEntryRepository(db)

        await repo.list_all(sort_order=SortOrder.desc)

        statement = db.scalars.await_args.args[0]
        assert "DESC" in str(statement)

    @pytest.mark.asyncio
    async def test_count_all_returns_total(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        db.scalar.return_value = 42
        repo = WatchEntryRepository(db)

        result = await repo.count_all()

        assert result == 42
        db.scalar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_all_returns_zero_when_none(self) -> None:
        db = AsyncMock(spec=AsyncSession)
        db.scalar.return_value = None
        repo = WatchEntryRepository(db)

        result = await repo.count_all()

        assert result == 0
