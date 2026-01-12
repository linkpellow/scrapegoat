"""
Type registry: Maps FieldType to parser/normalizer/validator functions.

Each type implements:
- parse(raw: str, smart_config: dict, context: ExtractionContext) -> tuple[value, reasons, errors]
- validate(value, rules: ValidationRules) -> tuple[is_valid, errors]
- score(value, raw, errors) -> float (confidence 0.0-1.0)
"""

from typing import Callable, Dict, Tuple, Any, List, Optional
from app.smartfields.types import FieldType, ExtractionContext, ValidationRules, SmartConfig

# Type alias for parser function
ParserFunc = Callable[[str, SmartConfig, ExtractionContext], Tuple[Any, List[str], List[str]]]


class TypeRegistry:
    """Registry of type-specific parsers, validators, and scorers"""
    
    _parsers: Dict[FieldType, ParserFunc] = {}
    
    @classmethod
    def register_parser(cls, field_type: FieldType, parser: ParserFunc):
        """Register a parser for a field type"""
        cls._parsers[field_type] = parser
    
    @classmethod
    def get_parser(cls, field_type: FieldType) -> Optional[ParserFunc]:
        """Get parser for a field type"""
        return cls._parsers.get(field_type)
    
    @classmethod
    def has_parser(cls, field_type: FieldType) -> bool:
        """Check if parser exists for field type"""
        return field_type in cls._parsers


# Default implementations will be registered by pattern modules
