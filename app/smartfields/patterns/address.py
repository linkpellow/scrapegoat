"""Address extraction with structured normalization"""

import re
from typing import Tuple, List, Any, Dict
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


# US state abbreviations
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

# US ZIP code regex
US_ZIP_REGEX = re.compile(r'\b\d{5}(?:-\d{4})?\b')


def parse_address(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize addresses.
    
    Output (structured):
    {
        "raw": "original address",
        "normalized": "cleaned address",
        "city": null,      # Optional if detectable
        "region": null,    # State/province
        "postal": null,    # ZIP/postal code
        "country": null
    }
    
    Normalization:
    - Trim and collapse whitespace
    - Normalize line breaks
    - Optional: extract components (city, state, zip)
    
    Conservative approach: don't invent missing components.
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Normalize whitespace and line breaks
    value = " ".join(raw.strip().split())
    reasons.append("normalized_whitespace")
    
    # Initialize structured output
    result: Dict[str, Any] = {
        "raw": raw,
        "normalized": value,
        "city": None,
        "region": None,
        "postal": None,
        "country": context.country
    }
    
    # Try to extract ZIP code (US)
    zip_match = US_ZIP_REGEX.search(value)
    if zip_match:
        result["postal"] = zip_match.group(0)
        reasons.append("extracted_zip_code")
    
    # Try to extract state (US) - look for 2-letter state codes
    words = value.upper().split()
    for word in words:
        if word in US_STATES:
            result["region"] = word
            reasons.append("extracted_state")
            break
    
    reasons.append("normalized_successfully")
    return result, reasons, errors


def parse_city(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse city name (simple normalization)"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = " ".join(raw.strip().split())
    reasons.append("normalized_whitespace")
    
    if smart_config.title_case:
        value = value.title()
        reasons.append("applied_title_case")
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


def parse_state(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse state/region (validate against known states if US)"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip().upper()
    
    # Validate US state
    if context.country == "US" and value not in US_STATES:
        errors.append("invalid_us_state")
        # Still return value in non-strict mode
        if smart_config.strict:
            return None, reasons, errors
    else:
        reasons.append("valid_us_state")
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


def parse_zip_code(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse ZIP/postal code"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip()
    
    # Validate US ZIP format
    if context.country == "US":
        if not US_ZIP_REGEX.match(value):
            errors.append("invalid_us_zip_format")
            if smart_config.strict:
                return None, reasons, errors
        else:
            reasons.append("valid_us_zip")
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


# Register parsers
TypeRegistry.register_parser(FieldType.ADDRESS, parse_address)
TypeRegistry.register_parser(FieldType.CITY, parse_city)
TypeRegistry.register_parser(FieldType.STATE, parse_state)
TypeRegistry.register_parser(FieldType.ZIP_CODE, parse_zip_code)
