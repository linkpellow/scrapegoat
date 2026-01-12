"""
HILR (Human-in-the-Rule) Engine

Learns from human interventions and proposes reusable rules.

Process:
1. Detect repeated intervention patterns
2. Create rule candidate
3. Collect confirmations
4. Auto-approve or require admin review
5. Apply rule to scope (domain/job/global)
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.rule_candidate import RuleCandidate
from app.models.intervention import InterventionTask
from app.models.field_map import FieldMap
from app.intelligence.adaptive_engine import extract_domain
import hashlib
import json


class HILREngine:
    """
    Human-in-the-Rule engine for learning from interventions.
    
    Detects patterns in human resolutions and proposes reusable rules.
    """
    
    # Minimum similarity threshold for pattern matching
    PATTERN_SIMILARITY_THRESHOLD = 0.8
    
    # Default confirmation requirements by rule type
    CONFIRMATION_THRESHOLDS = {
        "field_normalization": 3,
        "selector_pattern": 2,
        "auth_refresh_trigger": 1  # More critical, require manual approval faster
    }
    
    @staticmethod
    def detect_pattern(
        db: Session,
        intervention: InterventionTask
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if an intervention matches a known pattern.
        
        Returns:
            Pattern dict if matched, None otherwise
        """
        if intervention.type == "field_confirm" and intervention.status == "completed":
            return HILREngine._detect_field_normalization_pattern(intervention)
        
        elif intervention.type == "selector_fix" and intervention.status == "completed":
            return HILREngine._detect_selector_pattern(intervention)
        
        elif intervention.type == "login_refresh" and intervention.status == "completed":
            return HILREngine._detect_auth_pattern(intervention)
        
        return None
    
    @staticmethod
    def _detect_field_normalization_pattern(intervention: InterventionTask) -> Optional[Dict[str, Any]]:
        """Detect field normalization pattern"""
        payload = intervention.payload or {}
        resolution = intervention.resolution or {}
        
        field_type = payload.get("field_type")
        errors = payload.get("errors", [])
        action = resolution.get("action")
        
        if not field_type or not errors or action != "edit":
            return None
        
        # Create pattern signature
        error_pattern = sorted(errors)
        
        return {
            "type": "field_normalization",
            "field_type": field_type,
            "error_pattern": error_pattern,
            "raw_value_length_range": HILREngine._get_length_range(payload.get("raw_value", "")),
            "resolution": resolution
        }
    
    @staticmethod
    def _detect_selector_pattern(intervention: InterventionTask) -> Optional[Dict[str, Any]]:
        """Detect selector pattern (common selector failures)"""
        payload = intervention.payload or {}
        resolution = intervention.resolution or {}
        
        old_selector = payload.get("old_selector")
        new_selector = resolution.get("new_selector")
        
        if not old_selector or not new_selector:
            return None
        
        return {
            "type": "selector_pattern",
            "old_selector_pattern": HILREngine._extract_selector_pattern(old_selector),
            "new_selector_pattern": HILREngine._extract_selector_pattern(new_selector),
            "resolution": resolution
        }
    
    @staticmethod
    def _detect_auth_pattern(intervention: InterventionTask) -> Optional[Dict[str, Any]]:
        """Detect auth refresh pattern"""
        payload = intervention.payload or {}
        
        failure_code = payload.get("failure_code")
        if not failure_code:
            return None
        
        return {
            "type": "auth_refresh_trigger",
            "failure_code": failure_code,
            "resolution": intervention.resolution
        }
    
    @staticmethod
    def find_or_create_rule_candidate(
        db: Session,
        pattern: Dict[str, Any],
        intervention: InterventionTask,
        job_url: str
    ) -> RuleCandidate:
        """
        Find existing rule candidate or create new one.
        
        Args:
            db: Database session
            pattern: Detected pattern
            intervention: Intervention task
            job_url: Job URL (for domain extraction)
        
        Returns:
            RuleCandidate (existing or new)
        """
        rule_type = pattern["type"]
        
        # Generate pattern hash for matching
        pattern_hash = HILREngine._hash_pattern(pattern)
        
        # Look for existing candidate with similar pattern
        existing = db.query(RuleCandidate).filter(
            and_(
                RuleCandidate.rule_type == rule_type,
                RuleCandidate.status.in_(["pending", "approved"])
            )
        ).all()
        
        for candidate in existing:
            if HILREngine._patterns_match(pattern, candidate.trigger_pattern):
                # Found matching candidate - add confirmation
                domain = extract_domain(job_url)
                candidate.add_confirmation(
                    intervention_task_id=str(intervention.id),
                    resolution=intervention.resolution,
                    domain=domain
                )
                return candidate
        
        # No match - create new candidate
        domain = extract_domain(job_url)
        
        candidate = RuleCandidate(
            rule_type=rule_type,
            field_type=pattern.get("field_type"),
            trigger_pattern=pattern,
            proposed_rule=HILREngine._extract_proposed_rule(pattern),
            apply_scope="domain" if rule_type != "auth_refresh_trigger" else "job",
            scope_filter={"domain_pattern": f"*{domain}"} if rule_type != "auth_refresh_trigger" else None,
            required_confirmations=HILREngine.CONFIRMATION_THRESHOLDS.get(rule_type, 3)
        )
        
        candidate.add_confirmation(
            intervention_task_id=str(intervention.id),
            resolution=intervention.resolution,
            domain=domain
        )
        
        db.add(candidate)
        db.flush()
        
        return candidate
    
    @staticmethod
    def check_and_auto_approve(db: Session, candidate: RuleCandidate) -> bool:
        """
        Check if rule candidate should be auto-approved.
        
        Returns:
            True if auto-approved, False otherwise
        """
        if candidate.can_auto_approve():
            candidate.approve(approved_by="system_auto_approval")
            db.flush()
            return True
        return False
    
    @staticmethod
    def apply_rule_to_scope(
        db: Session,
        candidate: RuleCandidate
    ) -> int:
        """
        Apply approved rule to its scope.
        
        Returns:
            Number of entities affected
        """
        if candidate.status != "approved":
            return 0
        
        affected = 0
        
        if candidate.rule_type == "field_normalization":
            # Apply to field maps matching scope
            field_type = candidate.field_type
            proposed_rule = candidate.proposed_rule
            
            query = db.query(FieldMap).filter(FieldMap.field_type == field_type)
            
            # Apply scope filter
            if candidate.apply_scope == "domain":
                # TODO: Filter by domain pattern from scope_filter
                pass
            
            for field_map in query.all():
                # Update smart_config and validation_rules
                if "smart_config" in proposed_rule:
                    field_map.smart_config = {**field_map.smart_config, **proposed_rule["smart_config"]}
                if "validation_rules" in proposed_rule:
                    field_map.validation_rules = {**field_map.validation_rules, **proposed_rule["validation_rules"]}
                affected += 1
        
        # Mark as applied
        candidate.apply_rule()
        
        return affected
    
    # Helper methods
    
    @staticmethod
    def _get_length_range(value: str) -> str:
        """Get length range bucket (for pattern matching)"""
        length = len(value) if value else 0
        if length < 10:
            return "short"
        elif length < 50:
            return "medium"
        else:
            return "long"
    
    @staticmethod
    def _extract_selector_pattern(selector: str) -> str:
        """Extract generalized selector pattern"""
        # Simple heuristic: remove specific class/id values, keep structure
        import re
        # Replace specific values with wildcards
        pattern = re.sub(r'\d+', '*', selector)
        return pattern
    
    @staticmethod
    def _hash_pattern(pattern: Dict[str, Any]) -> str:
        """Generate hash for pattern matching"""
        # Create stable hash from pattern
        pattern_str = json.dumps(pattern, sort_keys=True)
        return hashlib.md5(pattern_str.encode()).hexdigest()[:8]
    
    @staticmethod
    def _patterns_match(pattern1: Dict[str, Any], pattern2: Dict[str, Any]) -> bool:
        """Check if two patterns are similar enough to match"""
        if pattern1.get("type") != pattern2.get("type"):
            return False
        
        pattern_type = pattern1.get("type")
        
        if pattern_type == "field_normalization":
            # Match if field_type and error_pattern are similar
            return (
                pattern1.get("field_type") == pattern2.get("field_type") and
                set(pattern1.get("error_pattern", [])) == set(pattern2.get("error_pattern", []))
            )
        
        elif pattern_type == "selector_pattern":
            # Match if selector patterns are similar
            return pattern1.get("old_selector_pattern") == pattern2.get("old_selector_pattern")
        
        elif pattern_type == "auth_refresh_trigger":
            # Match if failure code is same
            return pattern1.get("failure_code") == pattern2.get("failure_code")
        
        return False
    
    @staticmethod
    def _extract_proposed_rule(pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Extract proposed rule from pattern"""
        resolution = pattern.get("resolution", {})
        
        if pattern["type"] == "field_normalization":
            # Extract normalization config from resolution
            return {
                "smart_config": resolution.get("normalization_rule", {}),
                "validation_rules": {}
            }
        
        elif pattern["type"] == "selector_pattern":
            return {
                "selector_template": pattern.get("new_selector_pattern"),
                "selector_strategy": "pattern_based"
            }
        
        elif pattern["type"] == "auth_refresh_trigger":
            return {
                "session_ttl": 3600,  # Default 1 hour
                "refresh_strategy": "proactive"
            }
        
        return {}
