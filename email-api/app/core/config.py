"""Application configuration."""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment."""

    APP_NAME: str = "Faculty Email Classification API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database (PostgreSQL or SQLite for local run without Docker)
    DATABASE_URL: str = "sqlite+aiosqlite:///./email_platform.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-use-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS (must list origins when using credentials; * is not allowed)
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
    ALLOWED_ORIGINS_LIST: List[str] = []

    # Google OAuth (for "Sign in with Gmail")
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    BACKEND_URL: str = "http://localhost:8000"   # Backend base URL (for Google redirect_uri)
    FRONTEND_URL: str = "http://localhost:5173" # Where to redirect after Google login (with ?token=...)

    # Spark / Hive (optional; for production warehouse)
    SPARK_MASTER_URL: str = "spark://localhost:7077"
    HIVE_SERVER: str = "localhost:10000"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ALLOWED_ORIGINS_LIST = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
