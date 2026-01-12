"""
Session Lifecycle Stats API

Exposes session pool metrics for monitoring.
"""

from fastapi import APIRouter
from app.scraping.session_manager import get_session_manager

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/stats")
def get_session_stats():
    """
    Get current session pool statistics.
    
    Returns:
        Dict with session pool metrics
    """
    manager = get_session_manager()
    stats = manager.get_stats()
    
    return {
        "status": "ok",
        "session_pool": stats
    }


@router.post("/cleanup")
def cleanup_sessions():
    """
    Manually trigger session cleanup (removes expired sessions).
    
    Normally runs automatically, but can be triggered manually for testing.
    """
    manager = get_session_manager()
    manager.cleanup_expired()
    
    return {
        "status": "ok",
        "message": "Session cleanup completed"
    }
