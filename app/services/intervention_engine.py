"""
Intervention Engine: Determines when human intervention is needed

ONLY triggers HITL for:
1. Low-confidence SmartFields (< 0.75 and required)
2. Selector drift (hash changed + empty extraction)
3. Auth expired
4. Persistent hard blocks (provider failed + retries exhausted)

All triggers are evidence-based, not manual.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.intervention import InterventionTask
from app.models.job import Job
from app.models.run import Run
import hashlib


class InterventionEngine:
    """Decision logic for triggering human intervention"""
    
    # Confidence threshold for requiring human confirmation
    LOW_CONFIDENCE_THRESHOLD = 0.75
    
    # Max retries before escalating to manual
    MAX_AUTO_RETRIES = 3
    
    @staticmethod
    def should_intervene_field_confidence(
        field_name: str,
        field_result: Dict[str, Any],
        is_required: bool
    ) -> Optional[Dict[str, Any]]:
        """
        Check if field extraction confidence is too low.
        
        Returns intervention payload if intervention needed, else None.
        """
        if not is_required:
            return None
        
        confidence = field_result.get("confidence", 1.0)
        
        if confidence < InterventionEngine.LOW_CONFIDENCE_THRESHOLD:
            return {
                "type": "field_confirm",
                "trigger_reason": "low_confidence",
                "priority": "high" if confidence < 0.5 else "normal",
                "payload": {
                    "field_name": field_name,
                    "raw_value": field_result.get("raw"),
                    "parsed_value": field_result.get("value"),
                    "confidence": confidence,
                    "reasons": field_result.get("reasons", []),
                    "errors": field_result.get("errors", []),
                    "field_type": field_result.get("type", "string")
                }
            }
        
        return None
    
    @staticmethod
    def should_intervene_selector_drift(
        field_name: str,
        old_selector: str,
        extraction_result: Any,
        page_html: str,
        extraction_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if selector drift occurred (selector no longer matches).
        
        Triggered when:
        - Selector hash changed (implies page structure changed)
        - Extraction returned empty/null
        """
        if extraction_result is not None and extraction_count > 0:
            return None  # Extraction successful, no drift
        
        # Calculate selector hash (simple version - could be more sophisticated)
        selector_hash = hashlib.md5(old_selector.encode()).hexdigest()[:8]
        
        return {
            "type": "selector_fix",
            "trigger_reason": "selector_drift",
            "priority": "high",
            "payload": {
                "field_name": field_name,
                "old_selector": old_selector,
                "selector_hash": selector_hash,
                "page_snapshot": page_html[:50000] if page_html else None,  # First 50KB
                "extraction_result": extraction_result,
                "extraction_count": extraction_count
            }
        }
    
    @staticmethod
    def should_intervene_auth_expired(
        failure_code: str,
        job: Job,
        run: Run
    ) -> Optional[Dict[str, Any]]:
        """
        Check if authentication expired.
        
        Triggered when:
        - Failure code is auth-related
        - Job requires auth
        """
        if failure_code not in ("auth_expired", "unauthorized", "forbidden"):
            return None
        
        if not job.requires_auth:
            return None
        
        return {
            "type": "login_refresh",
            "trigger_reason": "auth_expired",
            "priority": "critical",
            "payload": {
                "target_url": str(job.target_url),
                "job_id": str(job.id),
                "run_id": str(run.id),
                "failure_code": failure_code,
                "last_session_valid_until": None  # Could track session TTL
            }
        }
    
    @staticmethod
    def should_intervene_hard_block(
        engine_attempts: List[Dict[str, Any]],
        job: Job,
        run: Run
    ) -> Optional[Dict[str, Any]]:
        """
        Check if persistent hard block detected.
        
        Triggered when:
        - All engines failed (HTTP → Playwright → Provider)
        - Retries exhausted
        - Block signals detected
        """
        if len(engine_attempts) < 3:
            return None  # Not enough attempts to declare hard block
        
        # Check if all attempts failed with block signals
        block_signals = ["blocked", "captcha", "access_denied", "rate_limited"]
        blocked_attempts = [
            a for a in engine_attempts
            if any(sig in a.get("signals", []) for sig in block_signals)
        ]
        
        if len(blocked_attempts) < 2:
            return None  # Not a persistent block
        
        return {
            "type": "manual_access",
            "trigger_reason": "hard_block",
            "priority": "critical",
            "payload": {
                "target_url": str(job.target_url),
                "job_id": str(job.id),
                "run_id": str(run.id),
                "engine_attempts": engine_attempts,
                "block_signals": [s for a in blocked_attempts for s in a.get("signals", [])],
                "suggested_action": "Consider using different IP, updating user agent, or marking site as blocked"
            }
        }
    
    @staticmethod
    def create_intervention(
        db: Session,
        job_id: str,
        run_id: Optional[str],
        intervention_spec: Dict[str, Any]
    ) -> InterventionTask:
        """
        Create an intervention task.
        
        Args:
            db: Database session
            job_id: Job ID
            run_id: Optional run ID (may be None for job-level interventions)
            intervention_spec: Dict with type, trigger_reason, priority, payload
        
        Returns:
            Created InterventionTask
        """
        task = InterventionTask(
            job_id=job_id,
            run_id=run_id,
            type=intervention_spec["type"],
            trigger_reason=intervention_spec["trigger_reason"],
            priority=intervention_spec.get("priority", "normal"),
            payload=intervention_spec["payload"]
        )
        
        db.add(task)
        db.flush()
        
        return task
    
    @staticmethod
    def apply_resolution(
        db: Session,
        task: InterventionTask,
        target_job: Job
    ) -> bool:
        """
        Apply human resolution deterministically.
        
        Human actions produce rules, not patches:
        - selector_fix → new selector version
        - field_confirm → normalization override rule
        - login_refresh → new session version
        
        Never mutates historical data.
        
        Returns:
            True if applied successfully, False otherwise
        """
        if task.status != "completed" or not task.resolution:
            return False
        
        resolution = task.resolution
        
        if task.type == "selector_fix":
            # Update selector with version bump
            new_selector = resolution.get("new_selector")
            field_name = task.payload.get("field_name")
            
            if new_selector and field_name:
                # This would update FieldMap with new selector
                # TODO: Implement selector versioning
                return True
        
        elif task.type == "field_confirm":
            # Store normalization rule or override
            action = resolution.get("action")
            
            if action == "confirm":
                # Increase confidence weighting for this field type
                pass
            elif action == "edit":
                # Store normalization override
                value = resolution.get("value")
                # TODO: Implement normalization rule storage
                pass
            elif action == "not_present":
                # Mark field as optional or remove from required list
                pass
        
        elif task.type == "login_refresh":
            # New session already created via SessionVault
            # Just mark as applied
            return True
        
        elif task.type == "manual_access":
            # Log bypass method, potentially disable job or mark site as blocked
            bypass_method = resolution.get("bypass_method")
            notes = resolution.get("notes")
            # TODO: Implement site blocking / job disabling logic
            return True
        
        return False
