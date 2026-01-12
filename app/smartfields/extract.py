"""
Main extraction orchestrator: Extract → Clean → Parse → Validate → Normalize → Score

This is the single entry point for all SmartField processing.
"""

from typing import Any, Dict, Optional
from app.smartfields.types import (
    FieldType, SmartFieldResult, ExtractionContext,
    ValidationRules, SmartConfig
)
from app.smartfields.registry import TypeRegistry
from app.smartfields.validate import validate_value
from app.smartfields.score import calculate_confidence

# Auto-import all pattern modules to register parsers
from app.smartfields.patterns import (
    email, phone, url, money, date,
    person_name, address, company, numeric, text
)
from app.services.multi_source_extraction import MultiSourceExtractor


def process_field(
    field_name: str,
    raw_value: Optional[str],
    field_type: str,
    smart_config: Optional[Dict[str, Any]],
    validation_rules: Optional[Dict[str, Any]],
    context: ExtractionContext
) -> SmartFieldResult:
    """
    Process a single field through the SmartFields pipeline.
    
    Pipeline:
    1. Extract (already done by engine - we receive raw_value)
    2. Clean (basic trim/normalize)
    3. Parse (type-specific parsing)
    4. Validate (type-specific + custom rules)
    5. Score (confidence calculation)
    6. Return evidence-backed result
    
    Args:
        field_name: Field name (for logging)
        raw_value: Raw extracted string
        field_type: Field type (e.g., "email", "phone")
        smart_config: Type-specific configuration
        validation_rules: Validation rules
        context: Extraction context (url, engine, locale, etc.)
    
    Returns:
        SmartFieldResult with value, raw, confidence, reasons, errors
    """
    # Initialize config objects
    smart = SmartConfig(**(smart_config or {}))
    rules = ValidationRules(**(validation_rules or {}))
    
    # Handle empty/null input
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        if rules.required:
            return SmartFieldResult(
                value=None,
                raw=raw_value,
                confidence=0.0,
                reasons=[],
                errors=["required_field_missing"],
                type=field_type
            )
        else:
            return SmartFieldResult(
                value=None,
                raw=raw_value,
                confidence=1.0,  # Not required, so null is valid
                reasons=["optional_field_not_provided"],
                errors=[],
                type=field_type
            )
    
    # Basic cleaning
    if isinstance(raw_value, str):
        raw_value = raw_value.strip()
    
    # Parse using type-specific parser
    try:
        field_type_enum = FieldType(field_type)
    except ValueError:
        # Unknown type - fallback to string
        field_type_enum = FieldType.STRING
    
    parser = TypeRegistry.get_parser(field_type_enum)
    
    if parser:
        # Type-specific parsing
        value, reasons, errors = parser(raw_value, smart, context)
    else:
        # No parser registered - treat as string
        value = raw_value
        reasons = ["no_parser_fallback_string"]
        errors = []
    
    # Validate
    validation_errors = validate_value(value, rules, field_type_enum)
    errors.extend(validation_errors)
    
    # Multi-Source Consensus (if HTML available in context)
    confidence_boost = 0.0
    sources_agreeing = 1
    
    if hasattr(context, 'page_html') and context.page_html:
        try:
            multi_source_result = MultiSourceExtractor.extract_all_sources(
                html=context.page_html,
                field_name=field_name,
                field_type=field_type,
                primary_value=value
            )
            
            # Use consensus value if available
            if multi_source_result["consensus_value"] is not None:
                value = multi_source_result["consensus_value"]
                confidence_boost = multi_source_result["confidence_boost"]
                sources_agreeing = multi_source_result["sources_agreeing"]
                
                if sources_agreeing >= 2:
                    reasons.append(f"consensus_{sources_agreeing}_sources")
        except Exception:
            # Silently fail multi-source extraction, use primary only
            pass
    
    # Score confidence (with multi-source boost)
    confidence = calculate_confidence(value, raw_value, errors, reasons)
    confidence = min(1.0, confidence + confidence_boost)
    
    # Build result
    result = SmartFieldResult(
        value=value,
        raw=raw_value,
        confidence=confidence,
        reasons=reasons,
        errors=errors,
        type=field_type
    )
    
    return result
