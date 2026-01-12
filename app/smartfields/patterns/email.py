"""Email extraction and validation - RFC-compliant with disposable domain checks"""

import re
from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


# RFC-like email regex (simplified but accurate for 99% of real emails)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)

# Common disposable email domains
DISPOSABLE_DOMAINS = {
    "tempmail.com", "guerrillamail.com", "10minutemail.com", "mailinator.com",
    "throwaway.email", "trashmail.com", "maildrop.cc", "yopmail.com"
}


def parse_email(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize email address.
    
    Normalization:
    - Lowercase domain
    - Strip mailto: prefix
    - Remove trailing punctuation
    - Trim whitespace
    
    Validation:
    - RFC-ish regex
    - Length bounds (3-254 chars)
    - Optional: disposable domain check
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Clean
    value = raw.strip()
    
    # Strip mailto:
    if value.lower().startswith("mailto:"):
        value = value[7:]
        reasons.append("stripped_mailto")
    
    # Remove trailing punctuation
    value = value.rstrip(".,;:")
    
    # Normalize case (domain only, but we'll lowercase entire address for simplicity)
    value = value.lower()
    reasons.append("normalized_case")
    
    # Length check
    if len(value) < 3 or len(value) > 254:
        errors.append("invalid_length")
        return None, reasons, errors
    
    # Regex validation
    if not EMAIL_REGEX.match(value):
        errors.append("invalid_email_format")
        return None, reasons, errors
    
    reasons.append("valid_format")
    
    # Extract domain
    try:
        domain = value.split("@")[1]
    except IndexError:
        errors.append("no_domain")
        return None, reasons, errors
    
    # Check disposable (optional, based on strict mode)
    if smart_config.strict and domain in DISPOSABLE_DOMAINS:
        errors.append("disposable_email")
        return None, reasons, errors
    
    if domain in DISPOSABLE_DOMAINS:
        reasons.append("disposable_domain_detected")
    
    reasons.append("parsed_successfully")
    return value, reasons, errors


# Register parser
TypeRegistry.register_parser(FieldType.EMAIL, parse_email)
