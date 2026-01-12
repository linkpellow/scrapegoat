from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class FieldType(str, Enum):
    """Supported SmartField types with deterministic parsing"""
    # Generic
    STRING = "string"
    TEXT = "text"
    HTML = "html"
    
    # Contact
    EMAIL = "email"
    PHONE = "phone"
    MOBILE = "mobile"
    FAX = "fax"
    
    # Location
    URL = "url"
    IMAGE_URL = "image_url"
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    ZIP_CODE = "zip_code"
    COUNTRY = "country"
    
    # Person/Business
    PERSON_NAME = "person_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    COMPANY = "company"
    JOB_TITLE = "job_title"
    
    # Numeric
    NUMBER = "number"
    INTEGER = "integer"
    DECIMAL = "decimal"
    MONEY = "money"
    PERCENTAGE = "percentage"
    
    # Temporal
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    
    # Other
    RATING = "rating"
    CATEGORY = "category"
    BOOLEAN = "boolean"


class SmartFieldResult(BaseModel):
    """
    Evidence-backed extraction result.
    Never silent failures - always includes confidence and reasons.
    """
    value: Optional[Any] = None          # Normalized/parsed value
    raw: Optional[str] = None            # Raw extracted string
    confidence: float = 0.0              # 0.0 - 1.0
    reasons: List[str] = []              # Success reasons (e.g., ["parsed_e164", "valid_us_number"])
    errors: List[str] = []               # Failure reasons (e.g., ["invalid_email_format"])
    type: str = "string"                 # Field type used
    
    class Config:
        extra = "allow"


class ExtractionContext(BaseModel):
    """Context passed to SmartFields for accurate parsing"""
    url: str
    fetched_at: str                      # ISO datetime
    engine: str                          # "http" | "playwright" | "provider"
    locale: str = "en-US"                # For date/number parsing
    timezone: str = "UTC"                # For datetime normalization
    country: str = "US"                  # For phone/address parsing
    page_html: Optional[str] = None      # Full page HTML for multi-source consensus
    
    class Config:
        extra = "allow"


class ValidationRules(BaseModel):
    """Validation rules for typed fields"""
    required: bool = False
    min_len: Optional[int] = None
    max_len: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None  # For email/url
    regex: Optional[str] = None
    must_parse: bool = True                       # Typed fields must parse successfully
    
    class Config:
        extra = "allow"


class SmartConfig(BaseModel):
    """Type-specific smart configuration"""
    # Phone
    country: Optional[str] = None
    format: Optional[str] = None         # "E164" | "NATIONAL" | "INTERNATIONAL"
    strict: bool = True
    allow_extensions: bool = False
    
    # URL
    force_https: bool = False
    strip_tracking: bool = False
    
    # Money
    currency: Optional[str] = None       # "USD" | "EUR" etc.
    
    # Date
    future_only: bool = False
    past_only: bool = False
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    
    # Text
    title_case: bool = False
    strip_html: bool = False
    
    class Config:
        extra = "allow"
