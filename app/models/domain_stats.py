"""
Domain-level performance statistics for adaptive intelligence.

Tracks historical success rates per domain × engine to bias AUTO decisions.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class DomainStats(Base):
    """
    Tracks execution statistics per domain to enable intelligent engine biasing.
    
    Example usage:
    - If httpbin.org has 5% HTTP success rate → skip HTTP, start with Playwright
    - If example.com has 95% HTTP success rate → always use HTTP first
    - If blocked domain → immediate provider escalation
    """
    __tablename__ = "domain_stats"
    __table_args__ = (
        UniqueConstraint('domain', 'engine', name='uq_domain_engine'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Domain identifier (normalized)
    domain = Column(String, nullable=False, index=True)
    
    # Engine tier ("http", "playwright", "provider")
    engine = Column(String, nullable=False, index=True)
    
    # Performance metrics
    total_attempts = Column(Integer, nullable=False, default=0)
    successful_attempts = Column(Integer, nullable=False, default=0)
    failed_attempts = Column(Integer, nullable=False, default=0)
    
    # Success rate (cached for fast queries)
    success_rate = Column(Float, nullable=False, default=0.0)
    
    # Average escalations when starting from this engine
    avg_escalations = Column(Float, nullable=False, default=0.0)
    
    # Total records extracted
    total_records = Column(Integer, nullable=False, default=0)
    
    # Average cost per successful record (in arbitrary units)
    avg_cost_per_record = Column(Float, nullable=False, default=0.0)
    
    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def update_stats(self, success: bool, records_extracted: int = 0, escalations: int = 0, cost: float = 0.0):
        """Update statistics after a run."""
        self.total_attempts += 1
        
        if success:
            self.successful_attempts += 1
            self.total_records += records_extracted
        else:
            self.failed_attempts += 1
        
        # Recalculate success rate
        if self.total_attempts > 0:
            self.success_rate = self.successful_attempts / self.total_attempts
        
        # Update average escalations (exponential moving average)
        alpha = 0.3  # Weight for new observations
        self.avg_escalations = (alpha * escalations) + ((1 - alpha) * self.avg_escalations)
        
        # Update average cost per record
        if self.total_records > 0:
            self.avg_cost_per_record = (self.avg_cost_per_record * (self.total_records - records_extracted) + cost) / self.total_records
