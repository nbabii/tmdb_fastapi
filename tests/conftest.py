import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


MOCK_MOVIE_RESPONSE = {
    "page": 1,
    "total_pages": 1,
    "total_results": 1,
    "results": [
        {
            "id": 550,
            "title": "Fight Club",
            "original_title": "Fight Club",
            "overview": "An insomniac office worker forms an underground fight club.",
            "release_date": "1999-10-15",
            "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
            "popularity": 73.4,
            "vote_average": 8.4,
            "vote_count": 26279,
            "genre_ids": [18, 53],
            "original_language": "en",
            "adult": False,
            "video": False,
        }
    ],
}

MOCK_TV_RESPONSE = {
    "page": 1,
    "total_pages": 1,
    "total_results": 1,
    "results": [
        {
            "id": 1396,
            "title": "Breaking Bad",
            "original_title": "Breaking Bad",
            "overview": "A chemistry teacher diagnosed with cancer turns to a life of crime.",
            "release_date": "2008-01-20",
            "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
            "backdrop_path": None,
            "popularity": 200.5,
            "vote_average": 9.5,
            "vote_count": 12000,
            "genre_ids": [18, 80],
            "original_language": "en",
            "adult": False,
            "video": False,
        }
    ],
}
