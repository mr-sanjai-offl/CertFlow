"""
Centralized application configuration.

All environment variables are read HERE and nowhere else.
Every other module imports settings from this file rather than reading
os.environ directly. This makes the configuration:
  - Easy to find (one file)
  - Easy to test (override the Settings object)
  - Easy to document (all variables listed in one place)

Interview note:
  If asked "where do you configure the database URL?" — point here.
  If asked "how would you add a new config variable?" — add a field
  to Settings and document it in .env.example.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Pydantic Settings automatically reads environment variables matching
    the field names (case-insensitive). A .env file is also supported.
    """

    # --- Database ---
    DATABASE_URL: str = "postgresql+pg8000://certflow:certflow@localhost:5432/certflow"

    # --- Redis (Celery broker + result backend) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Storage ---
    STORAGE_DIR: str = "./storage"

    # --- Limits ---
    MAX_RECIPIENTS_PER_JOB: int = 1000
    MAX_RETRIES: int = 3

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    # --- Security ---
    API_KEY: str | None = None

    # --- Environment ---
    ENVIRONMENT: str = "development"

    # --- CORS ---
    # Comma-separated origins. Use explicit trusted origins in production.
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Request limits ---
    API_REQUEST_SIZE_LIMIT: int = 10 * 1024 * 1024  # 10 MB

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using @lru_cache means the .env file is read once at startup,
    not on every request. This is standard practice with Pydantic Settings.
    """
    return Settings()
