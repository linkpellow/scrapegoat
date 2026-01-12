"""Company/organization name extraction"""

from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


def parse_company(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize company names.
    
    Conservative approach:
    - Trim whitespace
    - Collapse multiple spaces
    - No aggressive transformations
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Trim and collapse whitespace
    value = " ".join(raw.strip().split())
    reasons.append("normalized_whitespace")
    
    # Basic validation: at least 2 characters
    if len(value) < 2:
        errors.append("company_name_too_short")
        return None, reasons, errors
    
    reasons.append("normalized_successfully")
    return value, reasons, errors


# Register parser
TypeRegistry.register_parser(FieldType.COMPANY, parse_company)
TypeRegistry.register_parser(FieldType.JOB_TITLE, parse_company)  # Same logic
