"""Confidence scoring for SmartField results"""

from typing import Any, List, Optional


def calculate_confidence(
    value: Any,
    raw: Optional[str],
    errors: List[str],
    reasons: List[str]
) -> float:
    """
    Calculate confidence score (0.0 - 1.0) for an extraction result.
    
    Scoring logic:
    - Start at 1.0
    - Deduct for each error
    - Add bonus for successful parsing steps
    - Floor at 0.0
    
    This is deterministic and evidence-based, not probabilistic.
    """
    if value is None:
        # Null value
        if errors:
            return 0.0  # Failed extraction
        else:
            return 1.0  # Valid null (optional field)
    
    # Start with base confidence
    confidence = 1.0
    
    # Deduct for errors
    error_penalty = 0.2 * len(errors)
    confidence -= error_penalty
    
    # Bonus for successful parsing steps
    parsing_success_indicators = [
        "parsed_successfully",
        "valid_format",
        "valid_number",
        "normalized_successfully"
    ]
    
    successful_steps = sum(1 for r in reasons if r in parsing_success_indicators)
    if successful_steps > 0:
        confidence = min(1.0, confidence + 0.05 * successful_steps)
    
    # Penalty if raw was heavily modified (potential parsing ambiguity)
    if isinstance(raw, str) and isinstance(value, str):
        if len(raw) > 0 and len(value) < len(raw) * 0.5:
            confidence -= 0.1  # Significant data loss during parsing
            confidence = max(0.0, confidence)
    
    # Floor at 0.0
    confidence = max(0.0, confidence)
    
    # Ceiling at 1.0
    confidence = min(1.0, confidence)
    
    return round(confidence, 2)
