"""
Seed the database with up to 1000 movies fetched from the TMDB Discover API.

Usage:
    python scripts/seed_movies.py [--target 1000] [--batch 100] [--start-page 1]

Options:
    --target      Total number of movies to insert (default: 1000)
    --batch       How many movies to bulk-insert per DB commit (default: 100)
    --start-page  TMDB discover page to begin from (default: 1; max: 500)
"""

import argparse
import asyncio
import random
import sys
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, ".")  # allow `python scripts/seed_movies.py` from project root

from app.core.config import settings
from app.models.watched_movie import WatchedMovie


TMDB_HEADERS = {
    "Accept": "application/json",
    # TMDB_API_KEY is expected to be a Bearer (JWT) access token.
    # Classic v3 API keys are also supported via query param below as fallback.
}

# TMDB returns max 20 results per discover page; API caps at page 500.
TMDB_PAGE_SIZE = 20
TMDB_MAX_PAGE = 500


async def fetch_discover_page(client: httpx.AsyncClient, page: int) -> list[dict]:
    """Return raw movie dicts for a single /discover/movie page."""
    response = await client.get(
        "/discover/movie",
        params={
            "language": "en-US",
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "page": page,
        },
    )
    response.raise_for_status()
    return response.json().get("results", [])


async def fetch_existing_tmdb_ids(session_factory) -> set[int]:
    """Return all tmdb_ids already present in the DB."""
    async with session_factory() as session:
        rows = await session.scalars(select(WatchedMovie.tmdb_id))
        return set(rows.all())


def parse_release_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


_OVERVIEW_OPENERS = [
    "A gripping tale about",
    "An unforgettable journey through",
    "A thought-provoking story exploring",
    "A heart-pounding thriller about",
    "A touching drama centered on",
    "A visually stunning adventure featuring",
    "A darkly comedic look at",
    "An emotional rollercoaster following",
    "A bold reimagining of",
    "A suspenseful mystery surrounding",
]

_OVERVIEW_SUBJECTS = [
    "a lone detective chasing a ghost from the past",
    "two strangers thrown together by fate",
    "a family torn apart by secrets",
    "an unlikely hero who must save the world",
    "a scientist on the brink of a dangerous discovery",
    "a soldier haunted by what they left behind",
    "an artist whose work hides a dark truth",
    "a crew stranded millions of miles from home",
    "a child with extraordinary abilities",
    "rivals who discover they need each other",
]

_OVERVIEW_CLOSERS = [
    "in a race against time that will change everything.",
    "where every choice carries a devastating cost.",
    "and the truth is far more terrifying than the lies.",
    "as the line between good and evil blurs.",
    "only to find that some doors should stay closed.",
    "while the clock counts down to an inevitable end.",
    "in a world that refuses to play by the rules.",
    "before it's too late to turn back.",
    "and nothing — and no one — is what it seems.",
    "when the past finally catches up with the present.",
]


def random_overview() -> str:
    return (
        f"{random.choice(_OVERVIEW_OPENERS)} "
        f"{random.choice(_OVERVIEW_SUBJECTS)} "
        f"{random.choice(_OVERVIEW_CLOSERS)}"
    )


def random_date_watched() -> date:
    """Random date within the last 5 years."""
    start = date.today() - timedelta(days=5 * 365)
    offset = random.randint(0, 5 * 365)
    return start + timedelta(days=offset)


async def seed(target: int, batch_size: int, start_page: int) -> None:
    if not settings.TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY is not set in your .env file.")
        sys.exit(1)
    if not settings.DATABASE_URL:
        print("ERROR: DATABASE_URL is not set in your .env file.")
        sys.exit(1)

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    print("Fetching existing tmdb_ids from DB…")
    existing_ids = await fetch_existing_tmdb_ids(session_factory)
    print(f"  Found {len(existing_ids)} movies already in DB.")

    # TMDB supports two auth styles:
    #   - JWT read-access token  → Authorization: Bearer <token>
    #   - Classic v3 API key     → ?api_key=<key>
    # The .env value is a JWT, so use Bearer auth.
    api_key = settings.TMDB_API_KEY
    is_jwt = api_key.startswith("ey")
    auth_headers = {
        **TMDB_HEADERS,
        "Authorization": f"Bearer {api_key}",
    } if is_jwt else TMDB_HEADERS
    auth_params = {} if is_jwt else {"api_key": api_key}

    tmdb_client = httpx.AsyncClient(
        base_url=settings.TMDB_BASE_URL,
        headers=auth_headers,
        params=auth_params,
        timeout=30.0,
    )

    inserted_total = 0
    pending: list[WatchedMovie] = []
    page = start_page

    async with tmdb_client:
        while inserted_total < target:
            if page > TMDB_MAX_PAGE:
                print(f"Reached TMDB page limit ({TMDB_MAX_PAGE}). Stopping.")
                break

            try:
                results = await fetch_discover_page(tmdb_client, page)
            except httpx.HTTPStatusError as exc:
                print(f"TMDB error on page {page}: {exc.response.status_code} — skipping.")
                page += 1
                continue

            if not results:
                print(f"Page {page} returned no results. Stopping.")
                break

            for movie in results:
                tmdb_id = movie.get("id")
                title = movie.get("title") or movie.get("original_title")

                if not tmdb_id or not title:
                    continue
                if tmdb_id in existing_ids:
                    continue

                existing_ids.add(tmdb_id)
                pending.append(
                    WatchedMovie(
                        tmdb_id=tmdb_id,
                        title=title,
                        release_date=parse_release_date(movie.get("release_date")),
                        my_rating=random.randint(1, 10),
                        my_overview=random_overview(),
                        my_date_watched=random_date_watched(),
                    )
                )

                if len(pending) >= batch_size:
                    async with session_factory() as session:
                        session.add_all(pending)
                        await session.commit()
                    inserted_total += len(pending)
                    print(f"  Inserted {inserted_total}/{target} movies (page {page})…")
                    pending = []

                if inserted_total + len(pending) >= target:
                    break

            page += 1

    # Flush any remaining movies
    if pending:
        async with session_factory() as session:
            session.add_all(pending)
            await session.commit()
        inserted_total += len(pending)

    await engine.dispose()
    print(f"\nDone. Inserted {inserted_total} new movies into the database.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed DB with TMDB movies.")
    parser.add_argument("--target", type=int, default=1000, help="Number of movies to insert")
    parser.add_argument("--batch", type=int, default=100, help="Batch size per DB commit")
    parser.add_argument("--start-page", type=int, default=1, help="TMDB discover start page")
    args = parser.parse_args()

    asyncio.run(seed(args.target, args.batch, args.start_page))


if __name__ == "__main__":
    main()
