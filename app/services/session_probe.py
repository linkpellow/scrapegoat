"""
Proactive Session Health Probes

Validates sessions BEFORE job execution, not during.
Turns HITL into scheduled maintenance instead of runtime surprises.

Architecture:
- Lightweight HEAD requests
- Runs before job starts
- Creates refresh interventions proactively
- Tracks probe results for learning
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.session import SessionVault
from app.models.domain_config import DomainConfig
from app.enums import SessionHealthStatus
from app.services.intervention_engine import InterventionEngine


class SessionProbe:
    """Proactive session health checking."""
    
    @staticmethod
    async def probe_session_health(
        db: Session,
        session: SessionVault,
        probe_url: str,
        timeout: float = 3.0
    ) -> SessionHealthStatus:
        """
        Fast health check for a session.
        
        Args:
            session: SessionVault to probe
            probe_url: URL to test (homepage or search page)
            timeout: Request timeout in seconds
        
        Returns:
            SessionHealthStatus
        """
        try:
            # Extract cookies
            cookies = session.session_data.get("cookies", [])
            user_agent = session.session_data.get("user_agent", "Mozilla/5.0")
            
            # Convert to httpx format
            httpx_cookies = {c["name"]: c["value"] for c in cookies}
            
            # Fast HEAD request
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    probe_url,
                    cookies=httpx_cookies,
                    headers={"User-Agent": user_agent},
                    timeout=timeout,
                    follow_redirects=True
                )
            
            # Classify health
            if response.status_code == 200:
                status = SessionHealthStatus.VALID
            elif response.status_code in [401, 403]:
                status = SessionHealthStatus.INVALID
            elif response.status_code == 404:
                # Probe URL might be wrong, don't mark session invalid
                status = SessionHealthStatus.UNKNOWN
            else:
                status = SessionHealthStatus.UNKNOWN
            
            # Update session
            session.last_validated = datetime.utcnow()
            session.health_status = status.value
            session.is_valid = (status == SessionHealthStatus.VALID)
            
            # Log probe attempt
            validation_attempts = session.validation_attempts or []
            validation_attempts.append({
                "timestamp": datetime.utcnow().isoformat(),
                "status": status.value,
                "response_code": response.status_code,
                "probe_url": probe_url,
                "method": "proactive_probe"
            })
            session.validation_attempts = validation_attempts
            
            db.commit()
            
            return status
        
        except asyncio.TimeoutError:
            # Timeout - mark unknown, not invalid
            session.health_status = SessionHealthStatus.UNKNOWN.value
            session.last_validated = datetime.utcnow()
            db.commit()
            return SessionHealthStatus.UNKNOWN
        
        except Exception as e:
            # Network error - mark unknown
            session.health_status = SessionHealthStatus.UNKNOWN.value
            session.last_validated = datetime.utcnow()
            db.commit()
            return SessionHealthStatus.UNKNOWN
    
    @staticmethod
    async def probe_before_run(
        db: Session,
        domain: str,
        job_id: str,
        run_id: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Probe session health BEFORE starting a run.
        
        Returns:
            (is_healthy, intervention_id_if_created)
        
        If session invalid:
            - Creates login_refresh intervention
            - Returns (False, intervention_id)
        
        If session valid or not required:
            - Returns (True, None)
        """
        # Get domain config
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        # If domain doesn't require session, skip probe
        if not config or config.requires_session == "no":
            return (True, None)
        
        # Get session
        from app.services.session_manager import SessionManager
        session = SessionManager.get_valid_session(db, domain)
        
        if not session:
            # No session, but required
            if config.requires_session == "required":
                # Create intervention immediately
                task = InterventionEngine.create_intervention(
                    db=db,
                    job_id=job_id,
                    run_id=run_id,
                    intervention_spec={
                        "type": "manual_access",
                        "reason": "Session required but not available",
                        "priority": "high",
                        "payload": {
                            "domain": domain,
                            "action": "capture_session",
                            "probe_result": "no_session"
                        }
                    }
                )
                db.commit()
                return (False, str(task.id))
            else:
                # Optional session, proceed without
                return (True, None)
        
        # Probe session
        probe_url = f"https://{domain}"
        status = await SessionProbe.probe_session_health(db, session, probe_url)
        
        if status == SessionHealthStatus.INVALID:
            # Session invalid - create refresh intervention
            task = InterventionEngine.create_intervention(
                db=db,
                job_id=job_id,
                run_id=run_id,
                intervention_spec={
                    "type": "login_refresh",
                    "reason": "Session invalid (proactive probe)",
                    "priority": "normal",
                    "payload": {
                        "domain": domain,
                        "session_id": str(session.id),
                        "last_valid": session.last_validated.isoformat() if session.last_validated else None,
                        "action": "refresh_session",
                        "probe_result": "invalid"
                    }
                }
            )
            db.commit()
            return (False, str(task.id))
        
        elif status == SessionHealthStatus.UNKNOWN:
            # Unknown - proceed but log
            return (True, None)  # Don't block on unknown
        
        else:
            # Valid - proceed
            return (True, None)
    
    @staticmethod
    def should_probe_session(session: SessionVault) -> bool:
        """
        Determine if a session should be proactively probed.
        
        Probe if:
        - Last validated > 1 hour ago
        - Never validated
        - Nearing expiration (if known)
        """
        if not session.last_validated:
            return True
        
        # Probe if not validated in last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        if session.last_validated < hour_ago:
            return True
        
        # Probe if nearing expiration
        if session.expires_at:
            days_until_expiry = (session.expires_at - datetime.utcnow()).days
            if days_until_expiry < 2:  # Less than 2 days left
                return True
        
        return False
    
    @staticmethod
    async def batch_probe_sessions(db: Session, domain: Optional[str] = None):
        """
        Background task: Probe all sessions that need validation.
        
        Args:
            domain: Optional - only probe sessions for this domain
        
        This can be run periodically (e.g., every hour) to proactively
        validate sessions before they're needed.
        """
        query = db.query(SessionVault).filter(
            SessionVault.is_valid == True,
            SessionVault.health_status == SessionHealthStatus.VALID.value
        )
        
        if domain:
            query = query.filter(SessionVault.domain == domain)
        
        sessions = query.all()
        
        probed = 0
        invalidated = 0
        
        for session in sessions:
            if SessionProbe.should_probe_session(session):
                probe_url = f"https://{session.domain}"
                status = await SessionProbe.probe_session_health(db, session, probe_url)
                probed += 1
                
                if status == SessionHealthStatus.INVALID:
                    invalidated += 1
        
        return {
            "sessions_checked": len(sessions),
            "sessions_probed": probed,
            "sessions_invalidated": invalidated
        }
