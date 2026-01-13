"""
API Key Usage Endpoints

Provides endpoints to check API key usage and remaining credits.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.api_key_manager import ApiKeyManager

router = APIRouter()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/usage")
def get_api_key_usage(provider: Optional[str] = None):
    """
    Get API key usage statistics.
    
    Args:
        provider: Optional provider filter ("scraperapi", "scrapingbee", etc.)
    
    Returns:
        List of API key usage stats with remaining credits
    """
    key_manager = ApiKeyManager()
    stats = key_manager.get_usage_stats(provider=provider)
    
    return {
        "success": True,
        "provider": provider or "all",
        "keys": stats,
        "summary": {
            "total_keys": len(stats),
            "active_keys": sum(1 for s in stats if s["is_active"]),
            "total_credits": sum(s["total_credits"] for s in stats),
            "used_credits": sum(s["used_credits"] for s in stats),
            "remaining_credits": sum(s["remaining_credits"] for s in stats)
        }
    }


@router.post("/register")
def register_api_key(
    provider: str,
    api_key: str,
    total_credits: int,
    description: str = ""
):
    """
    Register a new API key with credit limit.
    
    Args:
        provider: "scraperapi", "scrapingbee", etc.
        api_key: The API key
        total_credits: Total credits available
        description: Optional description
    
    Returns:
        Registration confirmation
    """
    key_manager = ApiKeyManager()
    
    try:
        usage = key_manager.register_key(
            provider=provider,
            api_key=api_key,
            total_credits=total_credits,
            description=description
        )
        
        return {
            "success": True,
            "message": f"API key registered for {provider}",
            "key_id": usage.id,
            "total_credits": usage.total_credits,
            "remaining_credits": usage.remaining_credits
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
