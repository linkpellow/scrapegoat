"""Validation logic for SmartFields"""

import re
from typing import List, Any
from app.smartfields.types import ValidationRules, FieldType


def validate_value(value: Any, rules: ValidationRules, field_type: FieldType) -> List[str]:
    """
    Validate a parsed value against validation rules.
    
    Returns list of error messages (empty list if valid).
    """
    errors = []
    
    if value is None:
        if rules.required:
            errors.append("required_value_missing")
        return errors
    
    # String length validation
    if isinstance(value, str):
        if rules.min_len and len(value) < rules.min_len:
            errors.append(f"min_length_violation:{rules.min_len}")
        if rules.max_len and len(value) > rules.max_len:
            errors.append(f"max_length_violation:{rules.max_len}")
    
    # Numeric range validation
    if isinstance(value, (int, float)):
        if rules.min_value is not None and value < rules.min_value:
            errors.append(f"min_value_violation:{rules.min_value}")
        if rules.max_value is not None and value > rules.max_value:
            errors.append(f"max_value_violation:{rules.max_value}")
    
    # Allowed values (enum)
    if rules.allowed_values and value not in rules.allowed_values:
        errors.append("value_not_in_allowed_list")
    
    # Domain validation (for email/url)
    if rules.allowed_domains and field_type in (FieldType.EMAIL, FieldType.URL):
        if isinstance(value, str):
            if field_type == FieldType.EMAIL:
                domain = value.split("@")[-1] if "@" in value else ""
            else:  # URL
                from urllib.parse import urlparse
                domain = urlparse(value).netloc
            
            if domain and domain not in rules.allowed_domains:
                errors.append("domain_not_in_allowed_list")
    
    # Custom regex validation
    if rules.regex and isinstance(value, str):
        if not re.match(rules.regex, value):
            errors.append("custom_regex_validation_failed")
    
    return errors
