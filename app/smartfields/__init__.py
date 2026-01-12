"""
SmartFields: Deterministic typed extraction pipeline

Architecture:
    Extract → Clean → Parse → Validate → Normalize → Score → Persist (with evidence)

This module provides type-aware field processing for all scraping engines.
Engines return raw candidates; SmartFields does the rest.
"""

from app.smartfields.extract import process_field
from app.smartfields.types import FieldType, SmartFieldResult

__all__ = ["process_field", "FieldType", "SmartFieldResult"]
