"""Person name extraction with conservative normalization"""

import re
from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


def parse_person_name(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize person names.
    
    Normalization (conservative):
    - Trim whitespace
    - Collapse multiple spaces
    - Optional: title case (only if strict=false)
    
    No aggressive transformations - we don't guess structure.
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Trim and collapse whitespace
    value = " ".join(raw.strip().split())
    reasons.append("normalized_whitespace")
    
    # Optional title casing (only if non-strict)
    if not smart_config.strict and smart_config.title_case:
        value = value.title()
        reasons.append("applied_title_case")
    
    # Basic validation: at least 2 characters
    if len(value) < 2:
        errors.append("name_too_short")
        return None, reasons, errors
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


def parse_first_name(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse first name (same as person_name but stricter length)"""
    return parse_person_name(raw, smart_config, context)


def parse_last_name(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse last name (same as person_name)"""
    return parse_person_name(raw, smart_config, context)


# Register parsers
TypeRegistry.register_parser(FieldType.PERSON_NAME, parse_person_name)
TypeRegistry.register_parser(FieldType.FIRST_NAME, parse_first_name)
TypeRegistry.register_parser(FieldType.LAST_NAME, parse_last_name)
