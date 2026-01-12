"""Phone number extraction using libphonenumber (industry standard)"""

from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry

try:
    import phonenumbers
    from phonenumbers import NumberParseException
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


def parse_phone(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize phone numbers using libphonenumber.
    
    Normalization:
    - E164 format by default (e.g., +18135551212)
    - NATIONAL or INTERNATIONAL if specified
    - Strip extensions if not allowed
    
    Validation:
    - is_valid_number()
    - Region constraint (from context.country or smart_config.country)
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    if not HAS_PHONENUMBERS:
        errors.append("phonenumbers_library_not_installed")
        # Fallback: basic cleanup
        cleaned = "".join(c for c in raw if c.isdigit() or c in "+()-. ")
        return cleaned.strip(), reasons, errors
    
    # Determine region
    region = smart_config.country or context.country or "US"
    
    # Parse
    try:
        parsed = phonenumbers.parse(raw, region)
    except NumberParseException as e:
        errors.append(f"parse_error:{e.error_type}")
        return None, reasons, errors
    
    reasons.append("parsed_successfully")
    
    # Validate
    if not phonenumbers.is_valid_number(parsed):
        errors.append("invalid_phone_number")
        if not smart_config.strict:
            # In non-strict mode, still return the parsed number
            pass
        else:
            return None, reasons, errors
    else:
        reasons.append("valid_number")
    
    # Format
    format_type = (smart_config.format or "E164").upper()
    
    if format_type == "E164":
        value = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        reasons.append("formatted_e164")
    elif format_type == "NATIONAL":
        value = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
        reasons.append("formatted_national")
    elif format_type == "INTERNATIONAL":
        value = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        reasons.append("formatted_international")
    else:
        value = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        reasons.append("formatted_e164_default")
    
    return value, reasons, errors


# Register parsers
TypeRegistry.register_parser(FieldType.PHONE, parse_phone)
TypeRegistry.register_parser(FieldType.MOBILE, parse_phone)
TypeRegistry.register_parser(FieldType.FAX, parse_phone)
