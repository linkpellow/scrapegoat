from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.jobs import router as job_router
from app.api.interventions import router as intervention_router
from app.api import skip_tracing
from app.api.events import router as events_router
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

app.include_router(job_router)
app.include_router(intervention_router, prefix="/interventions", tags=["interventions"])
app.include_router(skip_tracing.router, prefix="/skip-tracing", tags=["skip-tracing"])
app.include_router(events_router, prefix="/events", tags=["events"])


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
            "events": "/events/runs/events"
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
