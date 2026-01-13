"""
API Key Manager - Manages multiple API keys with usage tracking

Supports:
- Multiple API keys per provider
- Automatic rotation when keys run out
- Usage tracking and credit monitoring
- Fallback to next available key
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import hashlib
import logging

from app.models.api_key_usage import ApiKeyUsage
from app.database import SessionLocal, get_db_session

logger = logging.getLogger(__name__)


def _hash_api_key(key: str) -> str:
    """Hash API key for storage (first 8 chars + hash)."""
    # Store first 8 chars for identification, hash the rest
    prefix = key[:8] if len(key) > 8 else key
    hash_suffix = hashlib.sha256(key.encode()).hexdigest()[:16]
    return f"{prefix}_{hash_suffix}"


class ApiKeyManager:
    """Manages API keys with usage tracking."""
    
    def __init__(self, db: Session = None):
        if db is None:
            self.db = SessionLocal()
            self._owns_db = True
        else:
            self.db = db
            self._owns_db = False
    
    def register_key(
        self,
        provider: str,
        api_key: str,
        total_credits: int,
        description: str = ""
    ) -> ApiKeyUsage:
        """
        Register a new API key with credit limit.
        
        Args:
            provider: "scrapingbee", "scraperapi", etc.
            api_key: The actual API key
            total_credits: Total credits available
            description: Optional description
        
        Returns:
            ApiKeyUsage record
        """
        key_id = _hash_api_key(api_key)
        
        # Check if key already exists
        existing = self.db.query(ApiKeyUsage).filter(
            ApiKeyUsage.id == key_id
        ).first()
        
        if existing:
            # Update credits if different
            if existing.total_credits != total_credits:
                existing.total_credits = total_credits
                existing.remaining_credits = total_credits - existing.used_credits
                existing.is_active = True
                logger.info(f"Updated credits for {provider} key: {total_credits}")
            return existing
        
        # Create new record
        usage = ApiKeyUsage(
            id=key_id,
            provider=provider,
            total_credits=total_credits,
            used_credits=0,
            remaining_credits=total_credits,
            is_active=True
        )
        
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        
        logger.info(f"Registered {provider} key with {total_credits} credits")
        return usage
    
    def get_available_key(
        self,
        provider: str,
        api_key: Optional[str] = None
    ) -> Optional[tuple[str, ApiKeyUsage]]:
        """
        Get an available API key for a provider.
        
        Args:
            provider: "scrapingbee", "scraperapi", etc.
            api_key: Optional specific key to use
        
        Returns:
            (api_key, ApiKeyUsage) or None if no keys available
        """
        if api_key:
            # Use specific key
            key_id = _hash_api_key(api_key)
            usage = self.db.query(ApiKeyUsage).filter(
                and_(
                    ApiKeyUsage.id == key_id,
                    ApiKeyUsage.provider == provider
                )
            ).first()
            
            if usage and usage.has_credits():
                return (api_key, usage)
            return None
        
        # Find best available key
        available = self.db.query(ApiKeyUsage).filter(
            and_(
                ApiKeyUsage.provider == provider,
                ApiKeyUsage.is_active == True,
                ApiKeyUsage.remaining_credits > 0
            )
        ).order_by(ApiKeyUsage.remaining_credits.desc()).first()
        
        if not available:
            logger.warning(f"No available {provider} keys with credits")
            return None
        
        # We need to return the actual key - match by hash
        from app.config import settings
        
        # Try to match the key from settings by hashing all available keys
        if provider == "scraperapi":
            for candidate_key in settings.get_scraperapi_keys():
                if _hash_api_key(candidate_key) == available.id:
                    return (candidate_key, available)
        elif provider == "scrapingbee":
            if settings.scrapingbee_api_key and _hash_api_key(settings.scrapingbee_api_key) == available.id:
                return (settings.scrapingbee_api_key, available)
        
        logger.warning(f"Could not resolve actual key for {provider} usage record {available.id}")
        return None
    
    def record_usage(
        self,
        provider: str,
        api_key: str,
        credits_used: int = 1
    ) -> bool:
        """
        Record API key usage.
        
        Args:
            provider: Provider name
            api_key: The API key used
            credits_used: Number of credits consumed
        
        Returns:
            True if successful, False if key not found or out of credits
        """
        key_id = _hash_api_key(api_key)
        
        usage = self.db.query(ApiKeyUsage).filter(
            and_(
                ApiKeyUsage.id == key_id,
                ApiKeyUsage.provider == provider
            )
        ).first()
        
        if not usage:
            logger.warning(f"API key usage record not found for {provider}")
            return False
        
        if not usage.has_credits() or usage.remaining_credits < credits_used:
            logger.warning(f"API key {provider} has insufficient credits: {usage.remaining_credits} < {credits_used}")
            usage.is_active = False
            self.db.commit()
            return False
        
        usage.use_credit(credits_used)
        self.db.commit()
        
        logger.info(f"Recorded {credits_used} credit(s) for {provider}. Remaining: {usage.remaining_credits}/{usage.total_credits}")
        return True
    
    def get_usage_stats(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get usage statistics for all keys or a specific provider.
        
        Returns:
            List of usage stats dicts
        """
        query = self.db.query(ApiKeyUsage)
        
        if provider:
            query = query.filter(ApiKeyUsage.provider == provider)
        
        usages = query.all()
        
        return [
            {
                "provider": u.provider,
                "key_id": u.id,
                "total_credits": u.total_credits,
                "used_credits": u.used_credits,
                "remaining_credits": u.remaining_credits,
                "is_active": u.is_active,
                "last_used_at": u.last_used_at.isoformat() if u.last_used_at else None
            }
            for u in usages
        ]
    
    def close(self):
        """Close database connection if we own it."""
        if hasattr(self, '_owns_db') and self._owns_db and hasattr(self, 'db') and self.db:
            self.db.close()
    
    def __del__(self):
        """Close database connection."""
        self.close()
