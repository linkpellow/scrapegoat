"""Numeric type extraction (integer, decimal, number, percentage, rating)"""

import re
from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


# Regex to extract numeric values
NUMBER_REGEX = re.compile(r'-?[\d,]+\.?\d*')
PERCENTAGE_REGEX = re.compile(r'([\d.]+)\s*%')


def parse_number(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse generic number (float)"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Extract numeric part
    match = NUMBER_REGEX.search(raw)
    if not match:
        errors.append("no_numeric_value")
        return None, reasons, errors
    
    numeric_str = match.group(0).replace(",", "")
    
    try:
        value = float(numeric_str)
    except ValueError:
        errors.append("invalid_numeric_format")
        return None, reasons, errors
    
    reasons.append("parsed_successfully")
    return value, reasons, errors


def parse_integer(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse integer"""
    value, reasons, errors = parse_number(raw, smart_config, context)
    
    if value is not None:
        try:
            value = int(value)
            reasons.append("converted_to_integer")
        except (ValueError, TypeError):
            errors.append("not_an_integer")
            return None, reasons, errors
    
    return value, reasons, errors


def parse_decimal(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse decimal (same as number, but ensures float)"""
    return parse_number(raw, smart_config, context)


def parse_percentage(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse percentage (returns decimal 0.0-1.0)"""
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    # Try percentage regex first
    match = PERCENTAGE_REGEX.search(raw)
    if match:
        try:
            value = float(match.group(1)) / 100.0
            reasons.append("parsed_percentage")
            return value, reasons, errors
        except ValueError:
            pass
    
    # Fallback: parse as number
    value, reasons, errors = parse_number(raw, smart_config, context)
    if value is not None and 0 <= value <= 100:
        value = value / 100.0
        reasons.append("assumed_percentage_0_100")
    
    return value, reasons, errors


def parse_rating(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """Parse rating (generic number, typically 0-5 or 0-10)"""
    return parse_number(raw, smart_config, context)


# Register parsers
TypeRegistry.register_parser(FieldType.NUMBER, parse_number)
TypeRegistry.register_parser(FieldType.INTEGER, parse_integer)
TypeRegistry.register_parser(FieldType.DECIMAL, parse_decimal)
TypeRegistry.register_parser(FieldType.PERCENTAGE, parse_percentage)
TypeRegistry.register_parser(FieldType.RATING, parse_rating)
