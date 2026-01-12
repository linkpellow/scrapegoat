"""
Page snapshots for replay-first HITL UI

Captures page state at time of extraction for deterministic replay.
Not live browser - recorded state.
"""

import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base


class PageSnapshot(Base):
    """
    Captured page state for HITL replay.
    
    Stores:
    - HTML content (compressed if large)
    - URL and metadata
    - Extraction context
    
    Used for showing humans the exact page state when extraction occurred.
    """
    __tablename__ = "page_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)
    
    # Page content
    url = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)  # Consider BYTEA + compression for large pages
    html_size = Column(Integer, nullable=False)  # Original size in bytes
    
    # Extraction context
    engine = Column(String, nullable=False)  # http | playwright | provider
    status_code = Column(Integer, nullable=True)
    
    # Metadata
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def truncate_html(self, max_bytes: int = 100000) -> str:
        """Return truncated HTML for API responses"""
        if len(self.html_content) <= max_bytes:
            return self.html_content
        return self.html_content[:max_bytes] + f"\n\n<!-- TRUNCATED: {len(self.html_content) - max_bytes} bytes omitted -->"
