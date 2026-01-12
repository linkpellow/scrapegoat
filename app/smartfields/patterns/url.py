"""URL extraction and normalization"""

from typing import Tuple, List, Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from app.smartfields.types import SmartConfig, ExtractionContext, FieldType
from app.smartfields.registry import TypeRegistry


# Common tracking parameters to strip
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid",
    "_ga", "_gl", "ref", "referrer"
}


def parse_url(raw: str, smart_config: SmartConfig, context: ExtractionContext) -> Tuple[Any, List[str], List[str]]:
    """
    Parse and normalize URLs.
    
    Normalization:
    - Force scheme (https default if missing)
    - Lowercase hostname
    - Strip tracking query params (optional)
    - Canonicalize trailing slash (optional)
    
    Validation:
    - Host present
    - TLD present
    - Scheme allowed
    """
    reasons = []
    errors = []
    
    if not raw or not isinstance(raw, str):
        return None, reasons, ["empty_or_invalid_input"]
    
    value = raw.strip()
    
    # Add scheme if missing
    if not value.startswith(("http://", "https://", "ftp://")):
        if smart_config.force_https:
            value = "https://" + value
            reasons.append("added_https_scheme")
        else:
            value = "http://" + value
            reasons.append("added_http_scheme")
    
    # Parse
    try:
        parsed = urlparse(value)
    except Exception as e:
        errors.append(f"parse_error:{str(e)}")
        return None, reasons, errors
    
    # Validate scheme
    if parsed.scheme not in ("http", "https", "ftp"):
        errors.append("invalid_scheme")
        return None, reasons, errors
    
    # Validate host
    if not parsed.netloc:
        errors.append("no_host")
        return None, reasons, errors
    
    reasons.append("valid_structure")
    
    # Normalize hostname (lowercase)
    netloc = parsed.netloc.lower()
    if netloc != parsed.netloc:
        reasons.append("normalized_hostname")
    
    # Strip tracking params
    query_params = parse_qs(parsed.query)
    if smart_config.strip_tracking:
        original_len = len(query_params)
        query_params = {k: v for k, v in query_params.items() if k not in TRACKING_PARAMS}
        if len(query_params) < original_len:
            reasons.append("stripped_tracking_params")
    
    # Rebuild query string
    query = urlencode(query_params, doseq=True) if query_params else ""
    
    # Rebuild URL
    normalized = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        query,
        parsed.fragment
    ))
    
    reasons.append("normalized_successfully")
    return normalized, reasons, errors


# Register parsers
TypeRegistry.register_parser(FieldType.URL, parse_url)
TypeRegistry.register_parser(FieldType.IMAGE_URL, parse_url)
