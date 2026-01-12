"""
Adaptive Intelligence Layer - Domain-Aware Engine Biasing

This module provides intelligent engine selection based on historical performance data.
It learns from past executions to make better AUTO decisions over time, while maintaining
full determinism and explainability.
"""
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.models.domain_stats import DomainStats


# Engine cost estimates (arbitrary units: 1.0 = baseline HTTP cost)
ENGINE_COSTS = {
    "http": 1.0,      # Baseline: fast, local Scrapy
    "playwright": 3.0,  # 3x cost: browser overhead
    "provider": 10.0,   # 10x cost: external API fees
}

# Confidence thresholds for biasing decisions
MIN_ATTEMPTS_FOR_BIAS = 5  # Need at least 5 attempts before biasing
LOW_SUCCESS_THRESHOLD = 0.20  # < 20% success = skip this engine
HIGH_SUCCESS_THRESHOLD = 0.85  # > 85% success = strong confidence


def extract_domain(url: str) -> str:
    """
    Extract normalized domain from URL.
    
    Examples:
        https://example.com/path -> example.com
        http://api.example.com:8080/endpoint -> api.example.com
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split('/')[0]
    
    # Remove port if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    return domain.lower()


def get_domain_stats(db: Session, domain: str, engine: str) -> Optional[DomainStats]:
    """Get historical stats for domain × engine combination."""
    return (
        db.query(DomainStats)
        .filter(DomainStats.domain == domain, DomainStats.engine == engine)
        .one_or_none()
    )


def record_run_outcome(
    db: Session,
    url: str,
    engine: str,
    success: bool,
    records_extracted: int = 0,
    escalations: int = 0
) -> None:
    """
    Record the outcome of a run to update domain stats.
    
    This is called after each run completes to maintain historical data.
    """
    domain = extract_domain(url)
    
    # Get or create stats for this domain × engine
    stats = get_domain_stats(db, domain, engine)
    if not stats:
        stats = DomainStats(domain=domain, engine=engine)
        db.add(stats)
    
    # Calculate cost
    cost = ENGINE_COSTS.get(engine, 1.0)
    
    # Update statistics
    stats.update_stats(
        success=success,
        records_extracted=records_extracted,
        escalations=escalations,
        cost=cost
    )
    
    db.commit()


def get_biased_initial_engine(
    db: Session,
    url: str,
    engine_mode: str = "auto"
) -> tuple[str, Optional[str]]:
    """
    Determine the optimal initial engine based on historical data.
    
    Returns:
        (engine, reason)
        - engine: "http", "playwright", or "provider"
        - reason: Explanation for the bias decision (or None if no bias applied)
    
    Decision logic:
    1. If engine_mode != "auto", return forced engine
    2. Check domain stats for HTTP
    3. If HTTP has low success rate (< 20%) and sufficient data → skip to Playwright
    4. If HTTP has high success rate (> 85%) → use HTTP with confidence
    5. Otherwise, default to HTTP (baseline)
    """
    # Forced mode - no biasing
    if engine_mode != "auto":
        return engine_mode, None
    
    domain = extract_domain(url)
    
    # Check HTTP stats first (since it's the default)
    http_stats = get_domain_stats(db, domain, "http")
    
    if http_stats and http_stats.total_attempts >= MIN_ATTEMPTS_FOR_BIAS:
        # We have enough data to make an informed decision
        
        if http_stats.success_rate < LOW_SUCCESS_THRESHOLD:
            # HTTP fails frequently on this domain → skip to Playwright
            return "playwright", (
                f"domain_bias:http_low_success:{http_stats.success_rate:.2%}"
                f"_attempts:{http_stats.total_attempts}"
            )
        
        elif http_stats.success_rate > HIGH_SUCCESS_THRESHOLD:
            # HTTP works well on this domain → use it confidently
            return "http", (
                f"domain_bias:http_high_success:{http_stats.success_rate:.2%}"
                f"_attempts:{http_stats.total_attempts}"
            )
    
    # Check if Playwright has been tried (maybe HTTP was never successful)
    playwright_stats = get_domain_stats(db, domain, "playwright")
    
    if playwright_stats and playwright_stats.total_attempts >= MIN_ATTEMPTS_FOR_BIAS:
        if playwright_stats.success_rate > HIGH_SUCCESS_THRESHOLD:
            # Playwright works well, and we probably have no good HTTP data
            return "playwright", (
                f"domain_bias:playwright_proven:{playwright_stats.success_rate:.2%}"
                f"_attempts:{playwright_stats.total_attempts}"
            )
    
    # Default: start with HTTP (no bias applied)
    return "http", None


def get_domain_intelligence_summary(db: Session, url: str) -> Dict[str, Any]:
    """
    Get a summary of historical intelligence for a domain.
    
    Useful for debugging and API endpoints.
    """
    domain = extract_domain(url)
    
    summary = {
        "domain": domain,
        "engines": {}
    }
    
    for engine in ["http", "playwright", "provider"]:
        stats = get_domain_stats(db, domain, engine)
        if stats:
            summary["engines"][engine] = {
                "total_attempts": stats.total_attempts,
                "success_rate": round(stats.success_rate, 4),
                "avg_escalations": round(stats.avg_escalations, 2),
                "total_records": stats.total_records,
                "avg_cost_per_record": round(stats.avg_cost_per_record, 2),
                "first_seen": stats.first_seen.isoformat(),
                "last_updated": stats.last_updated.isoformat(),
            }
        else:
            summary["engines"][engine] = None
    
    return summary


def should_skip_engine(db: Session, url: str, engine: str) -> tuple[bool, Optional[str]]:
    """
    Determine if an engine should be skipped based on historical data.
    
    Returns:
        (should_skip, reason)
    """
    domain = extract_domain(url)
    stats = get_domain_stats(db, domain, engine)
    
    if not stats or stats.total_attempts < MIN_ATTEMPTS_FOR_BIAS:
        return False, None
    
    # Skip if success rate is very low
    if stats.success_rate < LOW_SUCCESS_THRESHOLD:
        return True, (
            f"skip:{engine}:low_success:{stats.success_rate:.2%}"
            f"_attempts:{stats.total_attempts}"
        )
    
    return False, None
