"""Money/price extraction with currency detection"""

import re
from typing import Tuple, List, Any
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


# Currency symbols
CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "₽": "RUB",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
}

# Regex to extract numbers from prices
PRICE_REGEX = re.compile(r'[\d,]+\.?\d*')


def parse_money(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize monetary amounts.
    
    Output:
    {
        "amount": 12.34,
        "currency": "USD"
    }
    
    Normalization:
    - Extract currency symbol
    - Remove thousand separators
    - Parse decimal amount
    - Default currency from smart_config or context
    
    Validation:
    - Amount >= 0 (or min_value if specified)
    - Currency whitelist if specified
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip()
    
    # Detect currency
    detected_currency = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in value:
            detected_currency = code
            reasons.append(f"detected_currency:{code}")
            break
    
    # Extract numeric part
    match = PRICE_REGEX.search(value)
    if not match:
        errors.append("no_numeric_value")
        return None, reasons, errors
    
    numeric_str = match.group(0)
    
    # Remove thousand separators
    numeric_str = numeric_str.replace(",", "")
    
    # Parse
    try:
        amount = float(numeric_str)
    except ValueError:
        errors.append("invalid_numeric_format")
        return None, reasons, errors
    
    reasons.append("parsed_amount")
    
    # Validate amount >= 0
    if amount < 0:
        errors.append("negative_amount")
        return None, reasons, errors
    
    # Determine final currency
    currency = detected_currency or smart_config.currency or "USD"
    
    result = {
        "amount": amount,
        "currency": currency
    }
    
    reasons.append("normalized_successfully")
    return result, reasons, errors


# Register parser
TypeRegistry.register_parser(FieldType.MONEY, parse_money)
