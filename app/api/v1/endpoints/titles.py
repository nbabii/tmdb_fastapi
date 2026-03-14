from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.title import TitleSearchResponse, TitleType
from app.services.tmdb_client import tmdb_client

router = APIRouter()


@router.get("/search", response_model=TitleSearchResponse)
async def search_titles(
    query: str = Query(..., min_length=1, description="Title to search for"),
    type: TitleType = Query(..., description="Type of title to search for"),
    page: int = Query(default=1, ge=1, le=500),
    year: int | None = Query(default=None, description="Filter by release year"),
) -> TitleSearchResponse:
    try:
        data = await tmdb_client.search_titles(query=query, type=type, page=page, year=year)
        return TitleSearchResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"TMDB API error: {str(exc)}",
        ) from exc
