"""
Block Classifier - Determines if a failure should pause or fail.

Key logic:
- 403 + no session → create intervention, pause
- 403 + has session → session invalid, create refresh intervention, pause
- CAPTCHA → create intervention, pause
- Network errors → fail (not recoverable via HITL)
- Selector drift → create intervention, pause
"""

from typing import Optional, Dict, Any
from app.enums import DomainAccessClass


class BlockClassifier:
    """Classifies blocks and determines appropriate intervention type."""
    
    @staticmethod
    def should_pause_for_intervention(
        response_code: Optional[int],
        error_message: str,
        has_session: bool,
        domain_access_class: str = "public"
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Determine if a failure should pause for intervention.
        
        Returns:
            (should_pause, intervention_type, intervention_reason)
        
        Intervention types:
            - login_refresh: Session expired, needs refresh
            - manual_access: Site blocked, needs human session capture
            - selector_fix: Selectors drifted, needs update
            - captcha_solve: CAPTCHA challenge
        """
        
        # 403 Forbidden
        if response_code == 403:
            if has_session:
                # Session invalid → refresh needed
                return (True, "login_refresh", "Session expired or invalid (403 with session)")
            else:
                # No session → manual access needed
                return (True, "manual_access", "Hard block (403, no session)")
        
        # 401 Unauthorized
        if response_code == 401:
            return (True, "login_refresh", "Authentication required (401)")
        
        # CAPTCHA detected (heuristic)
        if "captcha" in error_message.lower() or "recaptcha" in error_message.lower():
            return (True, "captcha_solve", "CAPTCHA challenge detected")
        
        # Cloudflare challenge
        if "cloudflare" in error_message.lower() or "challenge" in error_message.lower():
            return (True, "manual_access", "Cloudflare challenge detected")
        
        # Selector extraction failed (possible drift)
        if "no items extracted" in error_message.lower() and response_code == 200:
            # Only pause if domain is known to require selectors
            if domain_access_class != DomainAccessClass.PUBLIC.value:
                return (True, "selector_fix", "No items extracted (possible selector drift)")
            else:
                # For public domains, might just be empty results
                return (False, None, None)
        
        # Rate limiting (429)
        if response_code == 429:
            # Don't pause for rate limiting - it's expected, just retry
            return (False, None, None)
        
        # Network errors (timeout, DNS, etc.) - not recoverable via HITL
        if response_code is None or "timeout" in error_message.lower() or "network" in error_message.lower():
            return (False, None, None)
        
        # Unknown error - default to fail, not pause
        return (False, None, None)
    
    @staticmethod
    def get_intervention_priority(intervention_type: str, block_rate: float = 0.0) -> str:
        """
        Determine intervention priority.
        
        Args:
            intervention_type: Type of intervention
            block_rate: Historical block rate for this domain (0.0-1.0)
        
        Returns:
            Priority: "low" | "normal" | "high" | "critical"
        """
        # High block rate → high priority (blocking many runs)
        if block_rate > 0.7:
            return "high"
        
        # CAPTCHA/manual access → normal (one-time fix)
        if intervention_type in ["manual_access", "captcha_solve"]:
            return "normal"
        
        # Session refresh → low (quick fix)
        if intervention_type == "login_refresh":
            return "low"
        
        # Selector fix → normal
        if intervention_type == "selector_fix":
            return "normal"
        
        return "normal"
