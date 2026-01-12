"""
RuleCandidate: Human-in-the-Rule (HILR) system

When humans resolve similar interventions repeatedly:
- System clusters similar decisions
- Proposes reusable rules
- Auto-applies after N confirmations or admin approval

This reduces HITL volume over time and makes the system self-improving.

Example:
- 3 jobs extract phone numbers with similar errors
- All humans fix by setting format="E164" and country="US"
- System proposes rule: "For phone fields on US domains, default to E164"
- After 2 more confirmations or 1 admin approval → rule auto-applies globally
"""

import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class RuleCandidate(Base):
    """
    HILR rule candidate for auto-applying human decisions.
    
    Lifecycle:
    1. System detects repeated intervention pattern
    2. Creates rule candidate
    3. Collects confirmations (subsequent similar resolutions)
    4. Admin reviews or auto-approves after threshold
    5. Rule applied to specified scope (domain/job/global)
    """
    __tablename__ = "rule_candidates"
    __table_args__ = (
        Index('ix_rule_candidates_status', 'status'),
        Index('ix_rule_candidates_field_type', 'field_type'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Rule identification
    rule_type = Column(String, nullable=False)  # field_normalization | selector_pattern | auth_refresh_trigger
    field_type = Column(String, nullable=True)  # email | phone | etc. (for field rules)
    
    # Pattern that triggered this candidate
    # For field_normalization: {error_pattern, raw_value_pattern, field_type}
    # For selector_pattern: {old_selector_pattern, domain_pattern}
    # For auth_refresh_trigger: {failure_code, domain_pattern}
    trigger_pattern = Column(JSONB, nullable=False)
    
    # Proposed rule
    # For field_normalization: {smart_config, validation_rules}
    # For selector_pattern: {selector_template, selector_strategy}
    # For auth_refresh_trigger: {session_ttl, refresh_strategy}
    proposed_rule = Column(JSONB, nullable=False)
    
    # Evidence (similar interventions that support this rule)
    # [{intervention_task_id, resolution, matched_at, domain}]
    supporting_evidence = Column(JSONB, nullable=False, default=list)
    
    # Confidence & approval
    confidence = Column(Float, nullable=False, default=0.0)  # Based on evidence count + consistency
    confirmations = Column(Integer, nullable=False, default=0)  # Count of supporting interventions
    required_confirmations = Column(Integer, nullable=False, default=3)  # Threshold for auto-approval
    
    # Status
    status = Column(String, nullable=False, default="pending")  # pending | approved | rejected | applied
    
    # Scope (where to apply)
    apply_scope = Column(String, nullable=False, default="domain")  # domain | job | global
    scope_filter = Column(JSONB, nullable=True)  # Domain pattern, job IDs, etc.
    
    # Approval tracking
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def add_confirmation(self, intervention_task_id: str, resolution: dict, domain: str):
        """Add supporting evidence from an intervention"""
        evidence = self.supporting_evidence or []
        evidence.append({
            "intervention_task_id": intervention_task_id,
            "resolution": resolution,
            "matched_at": func.now(),
            "domain": domain
        })
        self.supporting_evidence = evidence
        self.confirmations += 1
        
        # Update confidence based on evidence consistency
        self.confidence = min(1.0, 0.5 + (self.confirmations * 0.15))
    
    def can_auto_approve(self) -> bool:
        """Check if rule has enough confirmations for auto-approval"""
        return self.confirmations >= self.required_confirmations and self.status == "pending"
    
    def approve(self, approved_by: str = "system"):
        """Approve the rule for application"""
        self.status = "approved"
        self.approved_by = approved_by
        self.approved_at = func.now()
    
    def apply_rule(self):
        """Mark rule as applied"""
        self.status = "applied"
        self.applied_at = func.now()
    
    def reject(self, rejected_by: str = "system"):
        """Reject the rule"""
        self.status = "rejected"
        self.approved_by = rejected_by
        self.approved_at = func.now()
