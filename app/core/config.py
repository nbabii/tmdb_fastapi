from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TMDB_API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "FastAPI project"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
