"""
Provider Router - Intelligent routing for human-gated domains

Skip futile direct attempts and route to providers immediately
when domain is known to require infrastructure access.

Decision logic:
- access_class = "infra" → route to provider
- access_class = "human" + no session → route to provider OR create intervention
- access_class = "public" → standard auto-escalation

Benefits:
- Reduces noise (no failed HTTP attempts)
- Saves time (no waiting for escalation)
- Lower cost (provider only when needed)
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.domain_config import DomainConfig
from app.enums import DomainAccessClass, ExecutionStrategy


class ProviderRouter:
    """Intelligent routing based on domain characteristics."""
    
    # Provider preference order
    PROVIDER_PREFERENCE = [
        "scrapingbee",  # Best for JS-heavy sites
        "zyte",         # Good for large-scale
        "brightdata",   # Good for residential IPs
    ]
    
    @staticmethod
    def get_initial_strategy(
        db: Session,
        domain: str,
        has_session: bool,
        user_preference: Optional[str] = None
    ) -> tuple[ExecutionStrategy, str]:
        """
        Determine initial execution strategy based on domain classification.
        
        Args:
            domain: Target domain
            has_session: Whether valid session exists
            user_preference: Optional provider preference
        
        Returns:
            (ExecutionStrategy, reason)
        
        Decision tree:
        - PUBLIC → AUTO (standard escalation)
        - INFRA → PROVIDER (skip futile attempts)
        - HUMAN + has_session → AUTO (try with session)
        - HUMAN + no_session → depends on block_rate:
            - High block rate (>80%) → PROVIDER
            - Lower block rate → AUTO (might work)
        """
        # Get domain config
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        if not config:
            # Unknown domain - use AUTO
            return (ExecutionStrategy.AUTO, "unknown_domain_default_auto")
        
        access_class = config.access_class
        
        # PUBLIC domains → standard auto-escalation
        if access_class == DomainAccessClass.PUBLIC.value:
            return (ExecutionStrategy.AUTO, "public_domain")
        
        # INFRA domains → always use provider
        if access_class == DomainAccessClass.INFRA.value:
            # Use provider preference if set
            provider = user_preference or config.provider_preference or "scrapingbee"
            return (ExecutionStrategy.API_REPLAY, f"infra_domain_provider_{provider}")
        
        # HUMAN domains → depends on session availability
        if access_class == DomainAccessClass.HUMAN.value:
            if has_session:
                # Has session - try with it
                return (ExecutionStrategy.AUTO, "human_domain_with_session")
            else:
                # No session - check block rate
                if config.block_rate_403 >= 0.8:
                    # Very high block rate - use provider instead of failing
                    provider = user_preference or config.provider_preference or "scrapingbee"
                    return (ExecutionStrategy.API_REPLAY, f"human_domain_high_block_rate_provider_{provider}")
                else:
                    # Lower block rate - try AUTO (might work without session)
                    return (ExecutionStrategy.AUTO, "human_domain_low_block_rate")
        
        # Default fallback
        return (ExecutionStrategy.AUTO, "default")
    
    @staticmethod
    def should_skip_direct_attempts(
        db: Session,
        domain: str,
        has_session: bool
    ) -> bool:
        """
        Determine if direct scraping attempts should be skipped entirely.
        
        Returns True if:
        - Domain is INFRA (always needs provider)
        - Domain is HUMAN with very high block rate and no session
        """
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        if not config:
            return False
        
        # INFRA always skips direct
        if config.access_class == DomainAccessClass.INFRA.value:
            return True
        
        # HUMAN with high block rate and no session
        if config.access_class == DomainAccessClass.HUMAN.value:
            if not has_session and config.block_rate_403 >= 0.8:
                return True
        
        return False
    
    @staticmethod
    def get_provider_config(
        db: Session,
        domain: str,
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get provider configuration for a domain.
        
        Returns provider settings like:
        - API key (from env)
        - Rendering options (js, premium_proxy, etc.)
        - Timeout settings
        """
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        # Determine provider
        if not provider_name:
            provider_name = config.provider_preference if config else "scrapingbee"
        
        # Base configs per provider
        if provider_name == "scrapingbee":
            return {
                "provider": "scrapingbee",
                "render_js": True,
                "premium_proxy": False,  # Use premium only if standard fails
                "block_resources": True,  # Block images/fonts for speed
                "wait_for": None,  # Optional: wait for selector
                "timeout": 30000
            }
        
        elif provider_name == "zyte":
            return {
                "provider": "zyte",
                "render_js": True,
                "country": "US",
                "timeout": 30000
            }
        
        elif provider_name == "brightdata":
            return {
                "provider": "brightdata",
                "render_js": True,
                "country": "US",
                "timeout": 30000
            }
        
        else:
            # Fallback
            return {
                "provider": "scrapingbee",
                "render_js": True,
                "timeout": 30000
            }
    
    @staticmethod
    def update_provider_stats(
        db: Session,
        domain: str,
        provider_name: str,
        success: bool
    ):
        """
        Update provider success rate for domain.
        
        This helps learn which providers work best for which domains.
        """
        config = db.query(DomainConfig).filter(
            DomainConfig.domain == domain
        ).first()
        
        if not config:
            return
        
        # Track overall provider success rate
        # (Could be expanded to per-provider tracking)
        if success:
            config.provider_success_rate = (
                (config.provider_success_rate or 0) * 0.9 + 0.1
            )  # Weighted average
        else:
            config.provider_success_rate = (
                (config.provider_success_rate or 0) * 0.9
            )
        
        # If provider working well, set as preference
        if config.provider_success_rate > 0.7:
            config.provider_preference = provider_name
        
        db.commit()
