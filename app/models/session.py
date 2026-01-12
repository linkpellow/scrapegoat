"""
Session Vault - Secure storage for captured authentication sessions.

Architecture:
- Domain-based (not job-based) for reuse across jobs
- Health tracking with proactive validation
- Automatic expiration handling
- Intervention linking for session capture workflow
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class SessionVault(Base):
    """
    Secure storage for authentication sessions.
    
    Session Lifecycle:
    1. Captured via HITL or provider
    2. Stored with health status = VALID
    3. Probed before each use
    4. Marked INVALID when probe fails
    5. New intervention created for refresh
    
    Never hard-code credentials. Always capture via intervention flow.
    """
    __tablename__ = "session_vaults"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Domain-based (not job-based) for broad reuse
    domain = Column(String, nullable=False, index=True)
    
    # Session data (cookies, headers, tokens)
    # Structure:
    # {
    #   "cookies": [{"name": "session_id", "value": "...", "domain": "..."}],
    #   "headers": {"Authorization": "Bearer ..."},
    #   "user_agent": "...",
    #   "local_storage": {...},
    #   "captured_method": "manual_export" | "playwright_capture" | "provider"
    # }
    session_data = Column(JSONB, nullable=False)
    
    # Lifecycle tracking
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_validated = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Estimated expiration
    
    # Health status
    is_valid = Column(Boolean, default=True)
    health_status = Column(String, default="valid")  # valid/invalid/unknown/expired
    
    # Intervention linkage (if captured via HITL)
    intervention_id = Column(UUID(as_uuid=True), ForeignKey("intervention_tasks.id"), nullable=True)
    
    # Metadata
    notes = Column(String, nullable=True)
    validation_attempts = Column(JSONB, default=list)  # History of probe attempts
    # Example: [{"timestamp": "...", "status": "valid", "response_code": 200}]
