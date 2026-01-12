"""
Session Lifecycle Management for Playwright Browsers

Treats browser sessions as reusable assets with trust tracking.
Reduces captchas and escalations by preserving session state.

Key Principle: This is state management, not evasion.

Features:
- Trust-based session reuse
- Disk persistence (survives restarts)
- Circuit breaker (protects IP reputation)
- Captcha rate tracking (key KPI)
- Observable trust scoring (debug-friendly)
"""

from __future__ import annotations

import time
import logging
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """
    A reusable browser session with trust tracking.
    
    Trust decays over time, failures, and usage.
    Sessions are retired when trust drops below threshold.
    """
    site_domain: str
    proxy_identity: Optional[str]  # None for no proxy, or proxy ID
    cookies: list[Dict[str, Any]]
    storage_state: Optional[Dict[str, Any]]
    
    # Lifecycle tracking
    first_seen_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_success_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    failure_streak: int = 0
    total_uses: int = 0
    captcha_count: int = 0  # Track captcha encounters
    
    # Metadata
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    
    def session_key(self) -> Tuple[str, str]:
        """Unique key for this session (site_domain, proxy_identity)"""
        return (self.site_domain, self.proxy_identity or "default")
    
    def age_minutes(self) -> float:
        """Age of session in minutes"""
        return (datetime.now(timezone.utc) - self.first_seen_time).total_seconds() / 60
    
    def minutes_since_success(self) -> float:
        """Minutes since last successful use"""
        return (datetime.now(timezone.utc) - self.last_success_time).total_seconds() / 60


@dataclass
class SiteCircuitBreaker:
    """
    Circuit breaker to prevent IP/account reputation damage.
    
    Pauses scraping for a site after consecutive failures.
    """
    site_domain: str
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False  # True = circuit broken, don't scrape
    
    def record_failure(self):
        """Record a failure"""
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now(timezone.utc)
    
    def record_success(self):
        """Record success, reset counter"""
        self.consecutive_failures = 0
        self.is_open = False
    
    def should_open(self, threshold: int = 10) -> bool:
        """Check if circuit should open"""
        return self.consecutive_failures >= threshold
    
    def should_close(self, cooldown_minutes: int = 30) -> bool:
        """Check if circuit should close (cooldown expired)"""
        if not self.last_failure_time:
            return True
        minutes_since = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds() / 60
        return minutes_since > cooldown_minutes


class SessionLifecycleManager:
    """
    Manages browser session lifecycle with trust-based reuse.
    
    Sessions are keyed by (site_domain, proxy_identity) to prevent
    trust pollution when proxies are added.
    
    Trust scoring:
    - Fresh sessions start at 100
    - Age, failures, and overuse decay trust
    - Recent success boosts trust
    - Sessions with trust < 40 are retired
    
    Features:
    - Disk persistence (survives restarts)
    - Circuit breaker (protects reputation)
    - Captcha tracking (key KPI)
    - Observable trust breakdown
    
    Thread-safe for concurrent scraping.
    """
    
    # Trust thresholds
    TRUST_HEALTHY = 70      # Reuse without concern
    TRUST_DEGRADED = 40     # Reuse but monitor
    TRUST_RETIRED = 40      # Below this, retire
    
    # Lifecycle limits
    MAX_AGE_MINUTES = 120   # Retire sessions older than 2 hours
    MAX_FAILURE_STREAK = 3  # Auto-retire after 3 consecutive failures
    MAX_USES = 100          # Soft limit before aggressive decay
    HARD_CAP_USES = 200     # Hard limit - always retire
    
    # Circuit breaker
    CIRCUIT_FAILURE_THRESHOLD = 10  # Consecutive failures before breaking
    CIRCUIT_COOLDOWN_MINUTES = 30   # How long to wait before retry
    
    # Persistence
    PERSISTENCE_DIR = ".sessions"
    MAX_PERSISTED_AGE_HOURS = 24  # Don't load sessions older than this
    
    def __init__(self, enable_persistence: bool = True):
        """
        Initialize session pool.
        
        Args:
            enable_persistence: Load/save sessions to disk
        """
        self._sessions: Dict[Tuple[str, str], BrowserSession] = {}
        self._circuit_breakers: Dict[str, SiteCircuitBreaker] = {}
        self._lock = Lock()  # Thread-safe access
        self._enable_persistence = enable_persistence
        
        # Stats tracking
        self._total_captchas = 0
        self._total_requests = 0
        
        # Load persisted sessions
        if enable_persistence:
            self._load_persisted_sessions()
        
        logger.info(f"🔄 SessionLifecycleManager initialized (persistence={enable_persistence})")
    
    def get_session(
        self,
        site_domain: str,
        proxy_identity: Optional[str] = None
    ) -> Optional[BrowserSession]:
        """
        Get existing trusted session for site+proxy combo.
        
        Returns None if no trusted session exists or circuit breaker is open.
        
        Args:
            site_domain: Target site domain
            proxy_identity: Optional proxy identifier (for future proxy support)
        
        Returns:
            BrowserSession if trusted session exists, None otherwise
        """
        # Check circuit breaker first
        if self._is_circuit_open(site_domain):
            logger.warning(
                f"⚡ Circuit breaker OPEN for {site_domain} "
                f"(too many failures, cooling down)"
            )
            return None
        
        session_key = (site_domain, proxy_identity or "default")
        
        with self._lock:
            if session_key not in self._sessions:
                return None
            
            session = self._sessions[session_key]
            trust_breakdown = self._calculate_trust_breakdown(session)
            trust = trust_breakdown["total_trust"]
            
            # Check hard cap (always retire)
            if session.total_uses >= self.HARD_CAP_USES:
                logger.info(
                    f"🚫 Hard cap reached for {site_domain} "
                    f"(uses={session.total_uses} >= {self.HARD_CAP_USES})"
                )
                del self._sessions[session_key]
                return None
            
            # Check if session is still trustworthy
            if trust >= self.TRUST_DEGRADED:
                logger.info(
                    f"♻️ Reusing session for {site_domain} "
                    f"(trust={trust:.0f}, age={session.age_minutes():.1f}m, "
                    f"uses={session.total_uses}, streak={session.failure_streak})"
                )
                return session
            else:
                logger.info(
                    f"🔄 Retiring session for {site_domain} "
                    f"(trust={trust:.0f} < {self.TRUST_RETIRED})"
                )
                del self._sessions[session_key]
                return None
    
    def create_session(
        self,
        site_domain: str,
        cookies: list[Dict[str, Any]],
        storage_state: Optional[Dict[str, Any]] = None,
        proxy_identity: Optional[str] = None,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None
    ) -> BrowserSession:
        """
        Create and store new browser session.
        
        Args:
            site_domain: Target site domain
            cookies: Session cookies from Playwright
            storage_state: Full storage state (cookies + localStorage)
            proxy_identity: Optional proxy identifier
            user_agent: User agent used
            viewport: Viewport dimensions
        
        Returns:
            New BrowserSession
        """
        session = BrowserSession(
            site_domain=site_domain,
            proxy_identity=proxy_identity,
            cookies=cookies,
            storage_state=storage_state,
            user_agent=user_agent,
            viewport=viewport
        )
        
        session_key = session.session_key()
        
        with self._lock:
            self._sessions[session_key] = session
        
        logger.info(f"🆕 Created new session for {site_domain} (key={session_key})")
        return session
    
    def mark_success(
        self,
        site_domain: str,
        proxy_identity: Optional[str] = None,
        had_captcha: bool = False
    ):
        """
        Mark session as successful, boosting trust.
        
        Resets failure streak and updates last success time.
        
        Args:
            site_domain: Target site
            proxy_identity: Optional proxy ID
            had_captcha: Whether this request encountered a captcha
        """
        session_key = (site_domain, proxy_identity or "default")
        
        # Track captcha rate
        self._total_requests += 1
        if had_captcha:
            self._total_captchas += 1
        
        with self._lock:
            if session_key in self._sessions:
                session = self._sessions[session_key]
                session.last_success_time = datetime.now(timezone.utc)
                session.failure_streak = 0  # Reset failures
                session.total_uses += 1
                
                if had_captcha:
                    session.captcha_count += 1
                
                trust_breakdown = self._calculate_trust_breakdown(session)
                trust = trust_breakdown["total_trust"]
                logger.info(
                    f"✅ Session success for {site_domain} "
                    f"(trust={trust:.0f}, uses={session.total_uses}, captcha={had_captcha})"
                )
                
                # Persist session after success
                if self._enable_persistence:
                    self._persist_session(session)
        
        # Reset circuit breaker on success
        self._record_site_success(site_domain)
    
    def mark_failure(
        self,
        site_domain: str,
        proxy_identity: Optional[str] = None
    ):
        """
        Mark session as failed, reducing trust.
        
        Increments failure streak. Auto-retires after 3 consecutive failures.
        Also updates circuit breaker for site-level failure tracking.
        """
        session_key = (site_domain, proxy_identity or "default")
        
        # Track request (even failures)
        self._total_requests += 1
        
        with self._lock:
            if session_key in self._sessions:
                session = self._sessions[session_key]
                session.failure_streak += 1
                session.total_uses += 1
                
                trust_breakdown = self._calculate_trust_breakdown(session)
                trust = trust_breakdown["total_trust"]
                
                # Auto-retire if too many failures
                if session.failure_streak >= self.MAX_FAILURE_STREAK:
                    logger.warning(
                        f"🚫 Auto-retiring session for {site_domain} "
                        f"({session.failure_streak} consecutive failures)"
                    )
                    del self._sessions[session_key]
                else:
                    logger.info(
                        f"⚠️ Session failure for {site_domain} "
                        f"(trust={trust:.0f}, streak={session.failure_streak})"
                    )
        
        # Update circuit breaker
        self._record_site_failure(site_domain)
    
    def _calculate_trust_breakdown(self, session: BrowserSession) -> Dict[str, float]:
        """
        Calculate trust score with observable breakdown.
        
        Returns breakdown of penalties/bonuses for debugging.
        
        Returns:
            Dict with trust score and component breakdown
        """
        base_trust = 100.0
        age_penalty = 0.0
        failure_penalty = 0.0
        success_bonus = 0.0
        usage_penalty = 0.0
        
        # Age penalty (sessions older than 1 hour decay)
        age_minutes = session.age_minutes()
        if age_minutes > 60:
            age_penalty = (age_minutes - 60) * 0.5
        
        # Hard age limit
        if age_minutes > self.MAX_AGE_MINUTES:
            return {
                "base_trust": base_trust,
                "age_penalty": -999,  # Signal hard limit
                "failure_penalty": 0,
                "success_bonus": 0,
                "usage_penalty": 0,
                "total_trust": 0.0
            }
        
        # Failure penalty (failures hurt trust)
        failure_penalty = session.failure_streak * 15
        
        # Success bonus (recent success restores trust)
        minutes_since_success = session.minutes_since_success()
        if minutes_since_success < 5:
            success_bonus = 20
        
        # Usage penalty (don't overuse same session)
        if session.total_uses > 50:
            usage_penalty = (session.total_uses - 50) * 1
        
        # Hard usage limit
        if session.total_uses > self.MAX_USES:
            usage_penalty += 50  # Aggressive decay
        
        # Calculate final trust
        total_trust = base_trust - age_penalty - failure_penalty + success_bonus - usage_penalty
        total_trust = max(0.0, min(100.0, total_trust))
        
        return {
            "base_trust": base_trust,
            "age_penalty": -age_penalty,
            "failure_penalty": -failure_penalty,
            "success_bonus": success_bonus,
            "usage_penalty": -usage_penalty,
            "total_trust": total_trust
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics for monitoring.
        
        Includes captcha rate (key KPI) and trust breakdown samples.
        
        Returns:
            Dict with pool stats
        """
        with self._lock:
            total_sessions = len(self._sessions)
            
            # Calculate captcha rate (key KPI)
            captcha_rate = (self._total_captchas / self._total_requests * 100) if self._total_requests > 0 else 0
            
            if total_sessions == 0:
                return {
                    "total_sessions": 0,
                    "healthy_sessions": 0,
                    "degraded_sessions": 0,
                    "avg_age_minutes": 0,
                    "avg_uses": 0,
                    "captcha_rate_pct": round(captcha_rate, 2),
                    "total_requests": self._total_requests,
                    "total_captchas": self._total_captchas,
                    "circuit_breakers_open": len([cb for cb in self._circuit_breakers.values() if cb.is_open])
                }
            
            healthy = 0
            degraded = 0
            total_age = 0
            total_uses = 0
            total_captchas = 0
            
            # Sample trust breakdown (first session for observability)
            sample_trust_breakdown = None
            
            for i, session in enumerate(self._sessions.values()):
                trust_breakdown = self._calculate_trust_breakdown(session)
                trust = trust_breakdown["total_trust"]
                
                if trust >= self.TRUST_HEALTHY:
                    healthy += 1
                elif trust >= self.TRUST_DEGRADED:
                    degraded += 1
                
                total_age += session.age_minutes()
                total_uses += session.total_uses
                total_captchas += session.captcha_count
                
                # Capture first session's trust breakdown as sample
                if i == 0:
                    sample_trust_breakdown = trust_breakdown
            
            return {
                "total_sessions": total_sessions,
                "healthy_sessions": healthy,
                "degraded_sessions": degraded,
                "avg_age_minutes": round(total_age / total_sessions, 2),
                "avg_uses": round(total_uses / total_sessions, 2),
                "avg_captchas_per_session": round(total_captchas / total_sessions, 2),
                "captcha_rate_pct": round(captcha_rate, 2),
                "total_requests": self._total_requests,
                "total_captchas": self._total_captchas,
                "circuit_breakers_open": len([cb for cb in self._circuit_breakers.values() if cb.is_open]),
                "sample_trust_breakdown": sample_trust_breakdown  # For debugging
            }
    
    def cleanup_expired(self):
        """
        Remove expired sessions from pool.
        
        Called periodically to prevent memory bloat.
        """
        with self._lock:
            expired_keys = []
            
            for session_key, session in self._sessions.items():
                trust_breakdown = self._calculate_trust_breakdown(session)
                trust = trust_breakdown["total_trust"]
                if trust < self.TRUST_RETIRED:
                    expired_keys.append(session_key)
            
            for key in expired_keys:
                del self._sessions[key]
            
            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired sessions")
    
    # Circuit breaker methods
    
    def _is_circuit_open(self, site_domain: str) -> bool:
        """Check if circuit breaker is open for site"""
        if site_domain not in self._circuit_breakers:
            return False
        
        breaker = self._circuit_breakers[site_domain]
        
        # Check if should open
        if breaker.should_open(self.CIRCUIT_FAILURE_THRESHOLD):
            breaker.is_open = True
            logger.warning(
                f"⚡ Circuit breaker OPENED for {site_domain} "
                f"({breaker.consecutive_failures} consecutive failures)"
            )
            return True
        
        # Check if should close (cooldown expired)
        if breaker.is_open and breaker.should_close(self.CIRCUIT_COOLDOWN_MINUTES):
            breaker.is_open = False
            breaker.consecutive_failures = 0
            logger.info(f"✅ Circuit breaker CLOSED for {site_domain} (cooldown expired)")
            return False
        
        return breaker.is_open
    
    def _record_site_success(self, site_domain: str):
        """Record success for circuit breaker"""
        if site_domain in self._circuit_breakers:
            self._circuit_breakers[site_domain].record_success()
    
    def _record_site_failure(self, site_domain: str):
        """Record failure for circuit breaker"""
        if site_domain not in self._circuit_breakers:
            self._circuit_breakers[site_domain] = SiteCircuitBreaker(site_domain=site_domain)
        
        self._circuit_breakers[site_domain].record_failure()
    
    # Persistence methods
    
    def _load_persisted_sessions(self):
        """Load sessions from disk on startup"""
        try:
            persist_dir = Path(self.PERSISTENCE_DIR)
            if not persist_dir.exists():
                return
            
            loaded_count = 0
            expired_count = 0
            
            for session_file in persist_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    # Convert datetime strings back to datetime objects
                    data["first_seen_time"] = datetime.fromisoformat(data["first_seen_time"])
                    data["last_success_time"] = datetime.fromisoformat(data["last_success_time"])
                    
                    # Check if too old
                    age_hours = (datetime.now(timezone.utc) - data["first_seen_time"]).total_seconds() / 3600
                    if age_hours > self.MAX_PERSISTED_AGE_HOURS:
                        expired_count += 1
                        session_file.unlink()  # Delete old session file
                        continue
                    
                    # Recreate session object
                    session = BrowserSession(**data)
                    session_key = session.session_key()
                    
                    self._sessions[session_key] = session
                    loaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to load session from {session_file}: {e}")
                    continue
            
            if loaded_count > 0:
                logger.info(f"📂 Loaded {loaded_count} persisted sessions (expired {expired_count})")
        
        except Exception as e:
            logger.warning(f"Failed to load persisted sessions: {e}")
    
    def _persist_session(self, session: BrowserSession):
        """Save session to disk"""
        try:
            persist_dir = Path(self.PERSISTENCE_DIR)
            persist_dir.mkdir(exist_ok=True)
            
            # Create filename from session key
            session_key = session.session_key()
            filename = f"{session_key[0]}_{session_key[1]}.json"
            filepath = persist_dir / filename
            
            # Convert to dict with datetime as ISO strings
            data = asdict(session)
            data["first_seen_time"] = session.first_seen_time.isoformat()
            data["last_success_time"] = session.last_success_time.isoformat()
            
            # Write to disk
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.warning(f"Failed to persist session: {e}")


# Global session manager instance
_session_manager: Optional[SessionLifecycleManager] = None


def get_session_manager() -> SessionLifecycleManager:
    """Get global session manager instance (singleton)"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionLifecycleManager()
    return _session_manager
