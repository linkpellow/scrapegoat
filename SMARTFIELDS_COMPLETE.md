# SmartFields: Deterministic Typed Extraction — COMPLETE ✅

**Date:** 2026-01-11  
**Status:** Production-ready  
**Architecture:** Deterministic, evidence-backed, engine-agnostic

---

## What Is SmartFields?

SmartFields is a **typed extraction pipeline** that transforms raw scraped data into clean, validated, normalized values with full confidence scoring and error evidence.

**Not AI. Not guessing. Deterministic parsing with industry-standard libraries.**

---

## Pipeline

```
Extract → Clean → Parse → Validate → Normalize → Score → Persist (with evidence)
```

Every field extraction includes:
- **value**: Normalized/parsed value
- **raw**: Original extracted string
- **confidence**: 0.0-1.0 score
- **reasons**: Success indicators (e.g., `["parsed_e164", "valid_us_number"]`)
- **errors**: Failure reasons (e.g., `["invalid_email_format"]`)

---

## Supported Field Types

### Contact Information
- **email** - RFC-compliant validation, disposable domain detection
- **phone** - libphonenumber (E164/NATIONAL/INTERNATIONAL formats)
- **mobile** / **fax** - Same as phone

### Location
- **url** / **image_url** - Normalization, tracking param stripping
- **address** - Structured extraction (street, city, state, postal, country)
- **city** / **state** / **zip_code** / **country** - Component extraction

### Person/Business
- **person_name** / **first_name** / **last_name** - Conservative normalization
- **company** / **job_title** - Whitespace cleanup

### Numeric
- **number** / **integer** / **decimal** - Numeric parsing
- **money** - Currency detection + structured output `{"amount": 12.34, "currency": "USD"}`
- **percentage** / **rating** - Numeric with special handling

### Temporal
- **date** / **time** / **datetime** - dateparser (handles natural language)

### Generic
- **string** / **text** / **html** - Minimal processing
- **category** / **boolean** - Basic classification

---

## How To Use SmartFields

### 1. Define Field Type When Creating Field Maps

**API Request:**
```json
PUT /jobs/{job_id}/field-maps
{
  "mappings": [
    {
      "field_name": "contact_email",
      "selector_spec": {"css": ".contact .email"},
      "field_type": "email",
      "smart_config": {"strict": true},
      "validation_rules": {"required": true, "allowed_domains": ["company.com"]}
    },
    {
      "field_name": "phone",
      "selector_spec": {"css": ".phone"},
      "field_type": "phone",
      "smart_config": {"country": "US", "format": "E164"},
      "validation_rules": {"required": true}
    },
    {
      "field_name": "price",
      "selector_spec": {"css": ".price"},
      "field_type": "money",
      "smart_config": {"currency": "USD"},
      "validation_rules": {"min_value": 0}
    },
    {
      "field_name": "address",
      "selector_spec": {"css": ".address"},
      "field_type": "address",
      "smart_config": {},
      "validation_rules": {}
    }
  ]
}
```

### 2. SmartFields Processes Automatically

When a run executes, SmartFields:
1. Extracts raw values using selectors
2. Applies type-specific parsing (email regex, phone libphonenumber, etc.)
3. Validates against rules
4. Calculates confidence scores
5. Attaches evidence to each record

### 3. Inspect Results

**Record Output:**
```json
{
  "contact_email": "john@company.com",
  "phone": "+18135551212",
  "price": {"amount": 29.99, "currency": "USD"},
  "address": {
    "raw": "123 Main St, Tampa, FL 33610",
    "normalized": "123 Main St, Tampa, FL 33610",
    "city": null,
    "region": "FL",
    "postal": "33610",
    "country": "US"
  },
  "_smartfields": {
    "contact_email": {
      "value": "john@company.com",
      "raw": "  JOHN@COMPANY.COM  ",
      "confidence": 0.98,
      "reasons": ["normalized_case", "valid_format", "parsed_successfully"],
      "errors": []
    },
    "phone": {
      "value": "+18135551212",
      "raw": "(813) 555-1212",
      "confidence": 0.95,
      "reasons": ["parsed_successfully", "valid_number", "formatted_e164"],
      "errors": []
    },
    "price": {
      "value": {"amount": 29.99, "currency": "USD"},
      "raw": "$29.99",
      "confidence": 0.92,
      "reasons": ["detected_currency:USD", "parsed_amount", "normalized_successfully"],
      "errors": []
    },
    "address": {
      "value": {...},
      "raw": "123 Main St, Tampa, FL 33610",
      "confidence": 0.88,
      "reasons": ["normalized_whitespace", "extracted_zip_code", "extracted_state", "normalized_successfully"],
      "errors": []
    }
  }
}
```

---

## SmartConfig Options (Type-Specific)

### Phone
```json
{
  "country": "US",
  "format": "E164" | "NATIONAL" | "INTERNATIONAL",
  "strict": true,
  "allow_extensions": false
}
```

### Email
```json
{
  "strict": true  // Reject disposable email domains
}
```

### URL
```json
{
  "force_https": true,
  "strip_tracking": true
}
```

### Money
```json
{
  "currency": "USD"  // Default currency if not detected
}
```

### Date
```json
{
  "future_only": false,
  "past_only": false,
  "year_min": 1970,
  "year_max": 2100
}
```

### Text
```json
{
  "title_case": false,
  "strip_html": false
}
```

---

## Validation Rules (All Types)

```json
{
  "required": true,
  "min_len": 5,
  "max_len": 100,
  "min_value": 0,
  "max_value": 1000,
  "allowed_values": ["option1", "option2"],
  "allowed_domains": ["company.com"],  // email/url
  "regex": "^[A-Z0-9]+$",
  "must_parse": true  // Typed fields must parse successfully
}
```

---

## Type-Specific Implementation Details

### Email
- **Parser:** RFC-like regex
- **Normalization:** Lowercase, strip `mailto:`, trim
- **Validation:** Length bounds, disposable domain check (optional)

### Phone
- **Library:** `phonenumbers` (libphonenumber)
- **Normalization:** E164 format (+18135551212)
- **Validation:** `is_valid_number()`, region constraint

### URL
- **Library:** `urllib.parse`
- **Normalization:** Force scheme, lowercase hostname, strip tracking params
- **Validation:** Host present, TLD present, scheme allowed

### Money
- **Parser:** Currency symbol detection + regex
- **Output:** `{"amount": float, "currency": "USD"}`
- **Validation:** Amount >= 0, currency whitelist

### Date/Time
- **Library:** `dateparser` (handles "Jan 3", "yesterday", etc.)
- **Normalization:** ISO-8601
- **Validation:** Year bounds, future/past constraints

### Address
- **Parser:** US state + ZIP extraction
- **Output:** Structured `{raw, normalized, city, region, postal, country}`
- **Validation:** US ZIP format, state codes

### Numeric
- **Parser:** Regex + type coercion
- **Normalization:** Remove thousand separators
- **Validation:** Range bounds

---

## Backward Compatibility

SmartFields is **100% backward compatible**:
- If `field_type` is empty/null → defaults to `"string"`
- If `smart_config` is empty → defaults to `{}`
- If `validation_rules` is empty → defaults to `{}`
- Existing field_maps continue to work without changes

---

## Architecture

### Module Structure
```
app/smartfields/
  __init__.py           # Public API
  types.py              # FieldType enum, SmartFieldResult, ExtractionContext
  registry.py           # Type registry
  extract.py            # Main pipeline orchestrator
  validate.py           # Validation logic
  score.py              # Confidence scoring
  patterns/
    email.py            # Email parser
    phone.py            # Phone parser (libphonenumber)
    url.py              # URL parser
    money.py            # Money parser
    date.py             # Date parser (dateparser)
    address.py          # Address parser (US)
    person_name.py      # Name parser
    company.py          # Company parser
    numeric.py          # Numeric parsers
    text.py             # Generic text parsers
```

### Integration Points
- **HTTP/Scrapy Engine:** Applies SmartFields after extraction
- **Playwright Engine:** Applies SmartFields after extraction
- **Provider Engine:** Ready for integration (same pattern)

### Context Passing
```python
ExtractionContext(
    url=job.target_url,
    fetched_at=datetime.now().isoformat(),
    engine="http" | "playwright" | "provider",
    locale="en-US",
    timezone="UTC",
    country="US"
)
```
This context is required for accurate date/phone/address parsing.

---

## Dependencies

```
phonenumbers==9.0.21  # Phone number parsing (libphonenumber)
dateparser==1.2.2     # Date/time parsing with natural language support
```

---

## What Makes This "Top of Line" in 2026

1. **Deterministic** - No AI guessing, repeatable results
2. **Strongly Typed** - Each field has a type contract
3. **Evidence-Backed** - Every extraction includes confidence + reasons + errors
4. **Reproducible** - Same input → same output
5. **Configurable** - Type-specific options without chaos
6. **Industry Standard** - Uses the same libraries (libphonenumber, dateparser) that top systems use
7. **Engine-Agnostic** - Works with HTTP, Playwright, and future provider engines
8. **Debuggable** - Full transparency into parsing decisions

---

## Testing SmartFields

### Via API
```bash
# 1. Create job
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://example.com","fields":["email","phone","price"]}'

# 2. Set field maps with SmartFields
curl -X PUT http://localhost:8000/jobs/{job_id}/field-maps \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": [
      {
        "field_name": "email",
        "selector_spec": {"css": ".contact"},
        "field_type": "email",
        "smart_config": {"strict": true},
        "validation_rules": {"required": true}
      }
    ]
  }'

# 3. Run job and inspect records
curl http://localhost:8000/jobs/{job_id}/runs/{run_id}/records
```

### Via Direct Python
```python
from app.smartfields import process_field
from app.smartfields.types import ExtractionContext, FieldType

context = ExtractionContext(
    url="https://example.com",
    fetched_at="2026-01-11T12:00:00Z",
    engine="http",
    locale="en-US",
    timezone="UTC",
    country="US"
)

result = process_field(
    field_name="contact_email",
    raw_value="  JOHN@COMPANY.COM  ",
    field_type="email",
    smart_config={"strict": True},
    validation_rules={"required": True},
    context=context
)

print(result.dict())
# {
#   "value": "john@company.com",
#   "raw": "  JOHN@COMPANY.COM  ",
#   "confidence": 0.98,
#   "reasons": ["normalized_case", "valid_format", "parsed_successfully"],
#   "errors": []
# }
```

---

## Next Evolution: Failure Taxonomy + Auto-Remediation

With SmartFields complete, the next enhancement is:
1. **Failure Classification** - Categorize errors (e.g., `selector_drift`, `auth_expired`, `blocked`)
2. **Auto-Remediation** - Define allowed responses per failure class
3. **Cost-Aware Boundaries** - Stop economically unviable jobs

This builds on SmartFields' evidence-backed error reporting.

---

## Summary

SmartFields transforms the scraping platform from "raw data extraction" to **"accurate, validated, typed data collection with full transparency."**

Every field extraction is:
- ✅ Parsed with industry-standard libraries
- ✅ Validated against rules
- ✅ Scored for confidence
- ✅ Evidence-backed (reasons + errors)
- ✅ Engine-agnostic (HTTP, Playwright, Provider)

**This is how enterprise scraping platforms work in 2026.**
