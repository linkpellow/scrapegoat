"""Generic text extraction (string, text, html, category, boolean)"""

import re
from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


def parse_string(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse generic string (minimal processing).
    
    Normalization:
    - Trim whitespace
    - Collapse multiple spaces
    - Optional: strip HTML tags
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip()
    
    # Strip HTML if requested
    if smart_config.strip_html:
        value = re.sub(r'<[^>]+>', '', value)
        reasons.append("stripped_html")
    
    # Collapse whitespace
    value = " ".join(value.split())
    reasons.append("normalized_whitespace")
    
    if not value:
        errors.append("empty_after_normalization")
        return None, reasons, errors
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


def parse_text(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse text (allows longer content, same as string)"""
    return parse_string(raw, smart_config, context)


def parse_html(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse HTML (preserve tags, only trim)"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip()
    reasons.append("preserved_html")
    
    return value, reasons, errors


def parse_category(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse category (same as string)"""
    return parse_string(raw, smart_config, context)


def parse_boolean(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse boolean.
    
    Recognizes: true/false, yes/no, 1/0, on/off
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip().lower()
    
    if value in ("true", "yes", "1", "on"):
        reasons.append("parsed_true")
        return True, reasons, errors
    elif value in ("false", "no", "0", "off"):
        reasons.append("parsed_false")
        return False, reasons, errors
    else:
        errors.append("unrecognized_boolean_value")
        return None, reasons, errors


# Register parsers
TypeRegistry.register_parser(FieldType.STRING, parse_string)
TypeRegistry.register_parser(FieldType.TEXT, parse_text)
TypeRegistry.register_parser(FieldType.HTML, parse_html)
TypeRegistry.register_parser(FieldType.CATEGORY, parse_category)
TypeRegistry.register_parser(FieldType.BOOLEAN, parse_boolean)
