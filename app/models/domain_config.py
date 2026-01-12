"""
Domain Configuration Model

Stores learned characteristics about target domains to optimize routing and reduce failures.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class DomainConfig(Base):
    """
    Per-domain configuration and learning.
    
    Tracks:
    - Access requirements (public/infra/human)
    - Session requirements
    - Success rates per engine
    - Provider preferences
    - Block patterns
    """
    __tablename__ = "domain_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String, unique=True, nullable=False, index=True)
    
    # Access classification
    access_class = Column(String, nullable=False, default="public")  # public/infra/human
    requires_session = Column(String, nullable=False, default="no")  # no/optional/required
    
    # Success tracking
    total_attempts = Column(Integer, default=0)
    successful_attempts = Column(Integer, default=0)
    block_rate_403 = Column(Float, default=0.0)  # % of 403 responses
    block_rate_captcha = Column(Float, default=0.0)  # % of CAPTCHA challenges
    
    # Engine performance
    engine_stats = Column(JSONB, default=dict)
    # Example: {"http": {"attempts": 10, "success": 2}, "playwright": {...}}
    
    # Provider routing
    provider_preference = Column(String, nullable=True)  # scrapingbee, zyte, brightdata
    provider_success_rate = Column(Float, default=0.0)
    
    # Session management
    session_avg_lifetime_days = Column(Float, nullable=True)  # Learned session duration
    last_session_refresh = Column(DateTime, nullable=True)
    
    # Block patterns
    block_patterns = Column(JSONB, default=dict)
    # Example: {"cloudflare": true, "recaptcha": true, "403_on_headless": true}
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(String, nullable=True)
