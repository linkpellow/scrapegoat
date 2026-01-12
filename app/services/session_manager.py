"""
Session Manager - Health probes, lifecycle management, auto-refresh.

Key behaviors:
1. Probe sessions before use
2. Mark invalid sessions
3. Create refresh interventions
4. Track session lifetime
5. Auto-route to provider when sessions consistently fail
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.session import SessionVault
from app.models.domain_config import DomainConfig
from app.enums import SessionHealthStatus, DomainAccessClass
from app.services.intervention_engine import InterventionEngine
import httpx


class SessionManager:
    """Manages session health and lifecycle."""
    
    @staticmethod
    def get_valid_session(db: Session, domain: str) -> Optional[SessionVault]:
        """
        Get a valid session for a domain, if one exists.
        
        Returns:
            SessionVault if valid session found, None otherwise
        """
        # Get most recently validated session
        session = db.query(SessionVault).filter(
            SessionVault.domain == domain,
            SessionVault.is_valid == True,
            SessionVault.health_status == SessionHealthStatus.VALID.value
        ).order_by(SessionVault.last_validated.desc()).first()
        
        return session
    
    @staticmethod
    async def probe_session(db: Session, session: SessionVault, probe_url: str) -> SessionHealthStatus:
        """
        Probe a session to verify it's still valid.
        
        Args:
            session: SessionVault to probe
            probe_url: URL to test (e.g., homepage or API endpoint)
        
        Returns:
            SessionHealthStatus (VALID/INVALID/UNKNOWN)
        """
        try:
            # Extract cookies from session_data
            cookies = session.session_data.get("cookies", [])
            user_agent = session.session_data.get("user_agent", "Mozilla/5.0")
            
            # Convert to httpx format
            httpx_cookies = {c["name"]: c["value"] for c in cookies}
            
            # Fast HEAD request to test
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    probe_url,
                    cookies=httpx_cookies,
                    headers={"User-Agent": user_agent},
                    timeout=5.0,
                    follow_redirects=True
                )
            
            # Determine health based on response
            if response.status_code == 200:
                status = SessionHealthStatus.VALID
            elif response.status_code in [401, 403]:
                status = SessionHealthStatus.INVALID
            else:
                status = SessionHealthStatus.UNKNOWN
            
            # Update session
            session.last_validated = datetime.utcnow()
            session.health_status = status.value
            session.is_valid = (status == SessionHealthStatus.VALID)
            
            # Log validation attempt
            validation_attempts = session.validation_attempts or []
            validation_attempts.append({
                "timestamp": datetime.utcnow().isoformat(),
                "status": status.value,
                "response_code": response.status_code,
                "probe_url": probe_url
            })
            session.validation_attempts = validation_attempts
            
            db.commit()
            
            return status
        
        except Exception as e:
            # Network error or timeout
            session.health_status = SessionHealthStatus.UNKNOWN.value
            db.commit()
            return SessionHealthStatus.UNKNOWN
    
    @staticmethod
    def mark_session_invalid(db: Session, session: SessionVault, reason: str):
        """Mark a session as invalid and log reason."""
        session.is_valid = False
        session.health_status = SessionHealthStatus.INVALID.value
        session.last_validated = datetime.utcnow()
        
        # Log validation attempt
        validation_attempts = session.validation_attempts or []
        validation_attempts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "status": "invalid",
            "reason": reason
        })
        session.validation_attempts = validation_attempts
        
        db.commit()
    
    @staticmethod
    def estimate_session_lifetime(db: Session, domain: str) -> Optional[int]:
        """
        Estimate session lifetime in days based on historical data.
        
        Returns:
            Average days until session expires, or None if unknown
        """
        # Get domain config
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        if config and config.session_avg_lifetime_days:
            return int(config.session_avg_lifetime_days)
        
        # Fallback: analyze session history
        sessions = db.query(SessionVault).filter(
            SessionVault.domain == domain,
            SessionVault.captured_at.isnot(None),
            SessionVault.expires_at.isnot(None)
        ).all()
        
        if sessions:
            lifetimes = [
                (s.expires_at - s.captured_at).days
                for s in sessions
                if s.expires_at and s.captured_at
            ]
            if lifetimes:
                avg = sum(lifetimes) / len(lifetimes)
                return int(avg)
        
        return None
    
    @staticmethod
    def should_refresh_session(session: SessionVault, buffer_days: int = 2) -> bool:
        """
        Check if a session should be proactively refreshed.
        
        Args:
            session: SessionVault to check
            buffer_days: Refresh this many days before expiration
        
        Returns:
            True if session should be refreshed
        """
        if not session.expires_at:
            return False
        
        refresh_threshold = session.expires_at - timedelta(days=buffer_days)
        return datetime.utcnow() >= refresh_threshold
    
    @staticmethod
    def update_domain_stats(
        db: Session,
        domain: str,
        success: bool,
        engine: str,
        response_code: Optional[int] = None,
        had_session: bool = False
    ):
        """
        Update domain configuration based on run outcome.
        
        This learns domain characteristics over time.
        """
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        if not config:
            config = DomainConfig(
                domain=domain,
                access_class=DomainAccessClass.PUBLIC.value,
                requires_session="no"
            )
            db.add(config)
        
        # Update attempt counts
        config.total_attempts += 1
        if success:
            config.successful_attempts += 1
        
        # Track 403 rate
        if response_code == 403:
            config.block_rate_403 = (
                (config.block_rate_403 * (config.total_attempts - 1) + 1) / config.total_attempts
            )
        
        # Update engine stats
        engine_stats = config.engine_stats or {}
        if engine not in engine_stats:
            engine_stats[engine] = {"attempts": 0, "success": 0}
        
        engine_stats[engine]["attempts"] += 1
        if success:
            engine_stats[engine]["success"] += 1
        
        config.engine_stats = engine_stats
        
        # Reclassify access requirements if needed
        if config.block_rate_403 > 0.8 and not had_session:
            # High block rate without session → requires session
            config.requires_session = "required"
            config.access_class = DomainAccessClass.HUMAN.value
        
        config.updated_at = datetime.utcnow()
        db.commit()
