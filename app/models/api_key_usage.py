"""
API Key Usage Tracking Model

Tracks usage of external API keys (ScrapingBee, ScraperAPI, etc.)
to monitor credit consumption and prevent overuse.
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class ApiKeyUsage(Base):
    """Track API key usage and remaining credits."""
    
    __tablename__ = "api_key_usage"
    
    id = Column(String, primary_key=True)  # API key itself (hashed or full)
    provider = Column(String, nullable=False)  # "scrapingbee", "scraperapi", etc.
    total_credits = Column(Integer, nullable=False, default=0)  # Total credits available
    used_credits = Column(Integer, nullable=False, default=0)  # Credits consumed
    remaining_credits = Column(Integer, nullable=False)  # Calculated: total - used
    is_active = Column(Boolean, nullable=False, default=True)  # Whether key is still usable
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ApiKeyUsage(provider={self.provider}, remaining={self.remaining_credits}/{self.total_credits})>"
    
    def use_credit(self, amount: int = 1):
        """Mark a credit as used."""
        if self.remaining_credits < amount:
            raise ValueError(f"Insufficient credits: {self.remaining_credits} < {amount}")
        
        self.used_credits += amount
        self.remaining_credits = self.total_credits - self.used_credits
        
        if self.remaining_credits <= 0:
            self.is_active = False
    
    def has_credits(self) -> bool:
        """Check if key has remaining credits."""
        return self.is_active and self.remaining_credits > 0
