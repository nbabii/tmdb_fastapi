from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TMDB API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "FastAPI wrapper for The Movie Database (TMDB) API"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["*"]

    TMDB_API_KEY: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p"

    DATABASE_URL: str = ""

    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
