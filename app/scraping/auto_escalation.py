"""
Auto-escalation engine for intelligent strategy selection.

Deterministic rules for when to escalate from HTTP → Playwright → Provider.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re


class EscalationSignal:
    """Signals that trigger escalation."""
    
    # JS Framework markers (HTTP → Playwright)
    JS_MARKERS = [
        r'<script[^>]*id=["\']__NEXT_DATA__["\']',  # Next.js
        r'data-reactroot',  # React
        r'data-react-helmet',  # React Helmet
        r'ng-version',  # Angular
        r'v-cloak',  # Vue.js
        r'<div[^>]*id=["\']app["\'][^>]*></div>',  # Empty app div (SPA)
        r'window\.__NUXT__',  # Nuxt.js
        r'__svelte',  # Svelte
    ]
    
    # Block/bot detection markers (Playwright → Provider)
    BLOCK_MARKERS = [
        r'checking your browser',
        r'access denied',
        r'verify you are human',
        r'cloudflare',
        r'ddos protection',
        r'please verify you are a human',
        r'captcha',
        r'are you a robot',
        r'unusual traffic',
        r'blocked',
    ]
    
    # Status codes that indicate blocks
    BLOCK_STATUS_CODES = [401, 403, 429]
    
    @classmethod
    def detect_js_app(cls, html: str) -> List[str]:
        """Detect JavaScript framework markers in HTML."""
        signals = []
        html_lower = html.lower()
        
        for pattern in cls.JS_MARKERS:
            if re.search(pattern, html_lower, re.IGNORECASE):
                signals.append(pattern.split(r'["\']')[0].replace('<', '').replace('script', 'script_tag'))
        
        return signals
    
    @classmethod
    def detect_block(cls, html: str, status_code: int) -> List[str]:
        """Detect block/bot detection signals."""
        signals = []
        
        # Check status code
        if status_code in cls.BLOCK_STATUS_CODES:
            signals.append(f"status_{status_code}")
        
        # Check HTML content
        html_lower = html.lower()
        for pattern in cls.BLOCK_MARKERS:
            if re.search(pattern, html_lower):
                signals.append(pattern.replace(' ', '_'))
        
        return signals
    
    @classmethod
    def detect_extraction_failure(cls, extracted_count: int, required_selectors: int) -> bool:
        """Detect if extraction confidence is too low."""
        if required_selectors == 0:
            return False
        
        # If we got 0 matches on any required selector, that's a failure
        return extracted_count == 0


class EscalationDecision:
    """Represents an escalation decision."""
    
    def __init__(
        self,
        from_engine: str,
        to_engine: str,
        reason: str,
        signals: List[str]
    ):
        self.from_engine = from_engine
        self.to_engine = to_engine
        self.reason = reason
        self.signals = signals
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_engine": self.from_engine,
            "to_engine": self.to_engine,
            "reason": self.reason,
            "signals": self.signals,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class AutoEscalationEngine:
    """
    Intelligent auto-escalation engine that selects the optimal extraction strategy.
    
    Escalation tiers:
    1. HTTP (Scrapy/requests) - fastest, cheapest
    2. Playwright (headless browser) - handles JS
    3. Provider (Zyte/ScrapingBee) - handles blocks
    """
    
    TIER_ORDER = ["http", "playwright", "provider"]
    
    # Domains known to aggressively block non-browser traffic
    # Skip HTTP entirely, start with Playwright
    HOSTILE_DOMAINS = {
        "www.fastpeoplesearch.com",
        "fastpeoplesearch.com",
    }
    
    def __init__(self, engine_mode: str = "auto", domain: str = None):
        """
        Args:
            engine_mode: "auto" (intelligent), "http", "playwright", or "provider" (forced)
            domain: Optional domain for intelligent routing
        """
        self.engine_mode = engine_mode
        self.domain = domain
        self.attempts: List[Dict[str, Any]] = []
    
    def should_escalate_from_http(
        self,
        html: str,
        status_code: int,
        extracted_count: int = None,
        required_selectors: int = None
    ) -> Optional[EscalationDecision]:
        """
        Determine if we should escalate from HTTP to Playwright.
        
        Triggers:
        - Block status codes (401/403/429) - HARD TRIGGER
        - JS framework detected in HTML
        - Extraction confidence failure (0 matches on required selectors)
        - Meta robots noindex (often JS-gated content)
        """
        signals = []
        
        # ⚡ CRITICAL: Check for block status codes FIRST
        # 403/401/429 = immediate escalation to browser
        if status_code in EscalationSignal.BLOCK_STATUS_CODES:
            signals.append(f"status_{status_code}")
            return EscalationDecision(
                from_engine="http",
                to_engine="playwright",
                reason="blocked_status_code",
                signals=signals
            )
        
        # Check for JS app markers
        js_signals = EscalationSignal.detect_js_app(html)
        if js_signals:
            signals.extend(js_signals)
            return EscalationDecision(
                from_engine="http",
                to_engine="playwright",
                reason="js_app_detected",
                signals=signals
            )
        
        # Check for extraction failure
        if extracted_count is not None and required_selectors is not None:
            if EscalationSignal.detect_extraction_failure(extracted_count, required_selectors):
                signals.append("extraction_failure")
                return EscalationDecision(
                    from_engine="http",
                    to_engine="playwright",
                    reason="extraction_confidence_fail",
                    signals=signals
                )
        
        # Check for robots noindex (often JS-gated)
        if '<meta name="robots" content="noindex"' in html.lower():
            signals.append("robots_noindex")
            return EscalationDecision(
                from_engine="http",
                to_engine="playwright",
                reason="robots_noindex",
                signals=signals
            )
        
        return None
    
    def should_escalate_from_playwright(
        self,
        html: str,
        status_code: int,
        navigation_failed: bool = False,
        captcha_detected: bool = False
    ) -> Optional[EscalationDecision]:
        """
        Determine if we should escalate from Playwright to Provider.
        
        Triggers:
        - Block status codes (401/403/429)
        - Block interstitial text detected
        - Navigation failures (repeated)
        - Captcha detected
        """
        signals = []
        
        # Check for block signals
        block_signals = EscalationSignal.detect_block(html, status_code)
        if block_signals:
            signals.extend(block_signals)
            return EscalationDecision(
                from_engine="playwright",
                to_engine="provider",
                reason="blocked_detected",
                signals=signals
            )
        
        # Check for navigation failure
        if navigation_failed:
            signals.append("navigation_failed")
            return EscalationDecision(
                from_engine="playwright",
                to_engine="provider",
                reason="navigation_failed",
                signals=signals
            )
        
        # Check for captcha
        if captcha_detected:
            signals.append("captcha")
            return EscalationDecision(
                from_engine="playwright",
                to_engine="provider",
                reason="captcha_detected",
                signals=signals
            )
        
        return None
    
    def get_initial_engine(self) -> str:
        """Get the initial engine based on mode."""
        if self.engine_mode == "auto":
            # Check if domain is known to be hostile to HTTP
            if self.domain in self.HOSTILE_DOMAINS:
                return "playwright"  # Skip HTTP entirely
            return "http"  # Start with cheapest
        else:
            return self.engine_mode  # Force specific engine
    
    def can_escalate(self, current_engine: str) -> bool:
        """Check if escalation is possible from current engine."""
        if self.engine_mode != "auto":
            return False  # No escalation in forced mode
        
        try:
            current_idx = self.TIER_ORDER.index(current_engine)
            return current_idx < len(self.TIER_ORDER) - 1
        except ValueError:
            return False
    
    def log_attempt(
        self,
        engine: str,
        status: int,
        signals: List[str],
        decision: str,
        success: bool = False
    ):
        """Log an extraction attempt."""
        self.attempts.append({
            "engine": engine,
            "status": status,
            "signals": signals,
            "decision": decision,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def get_attempts_log(self) -> List[Dict[str, Any]]:
        """Get all logged attempts."""
        return self.attempts


def generate_browser_profile(
    user_agent: Optional[str] = None,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    timezone: str = "America/New_York",
    locale: str = "en-US"
) -> Dict[str, Any]:
    """
    Generate a stable browser fingerprint profile for Playwright.
    
    This provides consistent headers/settings to reduce false blocks.
    Not full stealth (no evasion plugins), just stable fingerprinting.
    """
    if user_agent is None:
        # Use a common, non-suspicious user agent
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    return {
        "user_agent": user_agent,
        "viewport": {
            "width": viewport_width,
            "height": viewport_height
        },
        "timezone": timezone,
        "locale": locale,
        "accept_language": f"{locale},en;q=0.9"
    }
