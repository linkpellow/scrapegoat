from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.jobs import router as job_router
from app.api.interventions import router as intervention_router
from app.api import skip_tracing
from app.api.events import router as events_router
from app.api.session_stats import router as session_router
from app.api.debug import router as debug_router
from app.api.api_keys import router as api_keys_router
from app.database import init_db

app = FastAPI(title="Scraper Platform Control Plane")

# CORS middleware - allow requests from frontend and BrainScraper
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://brainscraper.io",
        "https://www.brainscraper.io",
        "https://*.railway.app",  # Allow Railway preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup() -> None:
    init_db()
    
    # Initialize API key tracking
    try:
        from app.services.api_key_manager import ApiKeyManager
        from app.config import settings
        import logging
        
        logger = logging.getLogger(__name__)
        key_manager = ApiKeyManager()
        
        # Register ScraperAPI keys
        scraperapi_keys = settings.get_scraperapi_keys()
        for key in scraperapi_keys:
            if key:
                try:
                    key_manager.register_key(
                        provider="scraperapi",
                        api_key=key,
                        total_credits=5000,  # ScraperAPI free tier
                        description="ScraperAPI free tier key"
                    )
                    logger.info(f"Registered ScraperAPI key with 5000 credits")
                except Exception as e:
                    logger.warning(f"Failed to register ScraperAPI key: {e}")
        
        # Register ScrapingBee key if present
        if settings.scrapingbee_api_key:
            try:
                key_manager.register_key(
                    provider="scrapingbee",
                    api_key=settings.scrapingbee_api_key,
                    total_credits=1000,  # Default, can be updated
                    description="ScrapingBee API key"
                )
                logger.info(f"Registered ScrapingBee key with 1000 credits")
            except Exception as e:
                logger.warning(f"Failed to register ScrapingBee key: {e}")
        
        key_manager.close()
    except Exception as e:
        # Don't fail startup if API key registration fails
        import logging
        logging.getLogger(__name__).warning(f"API key registration failed (non-critical): {e}")

app.include_router(job_router)
app.include_router(intervention_router, prefix="/interventions", tags=["interventions"])
app.include_router(skip_tracing.router, prefix="/skip-tracing", tags=["skip-tracing"])
app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(session_router)  # Session lifecycle stats
app.include_router(debug_router)  # Debug endpoints
app.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])  # API key usage tracking


@app.get("/")
async def root():
    return {
        "name": "Scraper Platform Control Plane",
        "version": "6.0.0",
        "status": "operational",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "health": "/health",
            "jobs": "/jobs",
            "runs": "/runs",
            "preview": "/preview",
            "list_wizard": "/list-wizard",
            "interventions": "/interventions",
            "skip_tracing": "/skip-tracing",
            "events": "/events/runs/events",
            "sessions": "/sessions/stats"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


# Simple settings storage (in production, use database)
_settings = {
    "default_strategy": "auto",
    "max_concurrent_runs": 3,
    "default_timeout": 30,
    "enable_notifications": False,
}


@app.get("/settings")
async def get_settings():
    return _settings


@app.put("/settings")
async def update_settings(settings: dict):
    _settings.update(settings)
    return _settings
