from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List
import os


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
    
    # External providers
    scrapingbee_api_key: str = ""
    
    # ScraperAPI keys (comma-separated or individual env vars)
    scraperapi_api_keys: str = ""  # Comma-separated list of keys
    
    def get_scraperapi_keys(self) -> List[str]:
        """Get list of ScraperAPI keys from environment."""
        keys = []
        
        # Check for comma-separated list
        if self.scraperapi_api_keys:
            keys.extend([k.strip() for k in self.scraperapi_api_keys.split(",") if k.strip()])
        
        # Check for individual keys (SCRAPERAPI_KEY_1, SCRAPERAPI_KEY_2, etc.)
        i = 1
        while True:
            key = os.getenv(f"SCRAPERAPI_KEY_{i}") or os.getenv(f"APP_SCRAPERAPI_KEY_{i}")
            if not key:
                break
            keys.append(key.strip())
            i += 1
        
        # Check for single key
        single_key = os.getenv("SCRAPERAPI_KEY") or os.getenv("APP_SCRAPERAPI_KEY")
        if single_key and single_key not in keys:
            keys.append(single_key.strip())
        
        return keys


settings = Settings()
