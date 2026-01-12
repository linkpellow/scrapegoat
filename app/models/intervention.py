"""
InterventionTask: First-class HITL concept

Human intervention is triggered by the system when:
- Confidence is low and field is required
- Selector drift detected
- Auth expired
- Persistent hard blocks

Human actions produce rules, not patches.
All interventions are auditable, resumable, and replayable.
"""

import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class InterventionTask(Base):
    """
    HITL intervention task queue.
    
    Triggered by the system (not manually).
    Resolved by humans (producing rules).
    Applied deterministically (no silent mutation).
    
    Intervention Types:
    - selector_fix: Selector drift detected, needs human click
    - field_confirm: Low-confidence field needs confirmation/correction
    - login_refresh: Auth expired, needs new session capture
    - manual_access: Persistent block, needs human workaround
    """
    __tablename__ = "intervention_tasks"
    __table_args__ = (
        Index('ix_intervention_status', 'status'),
        Index('ix_intervention_job', 'job_id'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True)
    
    # Intervention type (determines what human can do)
    type = Column(String, nullable=False)  # selector_fix | field_confirm | login_refresh | manual_access
    
    # Status lifecycle
    status = Column(String, nullable=False, default="pending")  # pending | in_progress | completed | expired | cancelled
    
    # What triggered this intervention
    trigger_reason = Column(String, nullable=False)  # low_confidence | selector_drift | auth_expired | hard_block
    
    # Context for human (what they see)
    # For selector_fix: {field_name, old_selector, page_snapshot, extraction_result}
    # For field_confirm: {field_name, raw_value, parsed_value, confidence, reasons, errors}
    # For login_refresh: {target_url, session_vault_id, failure_message}
    # For manual_access: {url, engine_attempts, block_reason}
    payload = Column(JSONB, nullable=False, default=dict)
    
    # Human resolution (structured decision)
    # For selector_fix: {new_selector, selector_version}
    # For field_confirm: {action: "confirm" | "edit" | "not_present", value?, normalization_rule?}
    # For login_refresh: {new_session_id, captured_at}
    # For manual_access: {bypass_method, notes}
    resolution = Column(JSONB, nullable=True)
    
    # Metadata
    priority = Column(String, nullable=False, default="normal")  # low | normal | high | critical
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expire stale tasks
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String, nullable=True)  # User ID or system identifier
    
    def mark_in_progress(self, user_id: str = "system"):
        """Mark task as being worked on"""
        self.status = "in_progress"
        self.resolved_by = user_id
    
    def complete(self, resolution: dict, user_id: str = "system"):
        """Complete task with resolution"""
        self.status = "completed"
        self.resolution = resolution
        self.resolved_at = func.now()
        self.resolved_by = user_id
    
    def expire(self):
        """Mark task as expired"""
        self.status = "expired"
    
    def cancel(self, reason: str = "cancelled"):
        """Cancel task"""
        self.status = "cancelled"
        if not self.resolution:
            self.resolution = {"cancelled_reason": reason}
