from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/scraper"
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Run behavior
    default_max_attempts: int = 3
    http_timeout_seconds: int = 20
    browser_nav_timeout_ms: int = 30000


settings = Settings()
