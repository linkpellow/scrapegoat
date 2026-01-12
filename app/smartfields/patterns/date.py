"""Date/datetime extraction using dateparser (handles natural language)"""

from typing import Tuple, List, Any
from datetime import datetime
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry

try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:
    HAS_DATEPARSER = False


def parse_date(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize dates.
    
    Normalization:
    - ISO-8601 format
    - Timezone-aware (from context.timezone)
    
    Validation:
    - Year bounds (default 1970-2100)
    - Optional: future_only or past_only
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    if not HAS_DATEPARSER:
        errors.append("dateparser_library_not_installed")
        # Fallback: return raw
        return raw.strip(), reasons, errors
    
    # Parse using dateparser (handles "Jan 3", "yesterday", "2026-01-11", etc.)
    settings = {
        "TIMEZONE": context.timezone,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "current_period"
    }
    
    parsed = dateparser.parse(raw, settings=settings)
    
    if not parsed:
        errors.append("unable_to_parse_date")
        return None, reasons, errors
    
    reasons.append("parsed_successfully")
    
    # Year bounds validation
    year_min = smart_config.year_min or 1970
    year_max = smart_config.year_max or 2100
    
    if not (year_min <= parsed.year <= year_max):
        errors.append(f"year_out_of_bounds:{parsed.year}")
        return None, reasons, errors
    
    reasons.append("year_valid")
    
    # Future/past validation
    now = datetime.now(parsed.tzinfo)
    
    if smart_config.future_only and parsed < now:
        errors.append("date_must_be_future")
        return None, reasons, errors
    
    if smart_config.past_only and parsed > now:
        errors.append("date_must_be_past")
        return None, reasons, errors
    
    # Normalize to ISO-8601
    value = parsed.isoformat()
    reasons.append("normalized_iso8601")
    
    return value, reasons, errors


# Register parsers
TypeRegistry.register_parser(FieldType.DATE, parse_date)
TypeRegistry.register_parser(FieldType.DATETIME, parse_date)
TypeRegistry.register_parser(FieldType.TIME, parse_date)
