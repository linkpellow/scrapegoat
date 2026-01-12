# Skip Tracing API Integration

**Purpose:** Wrap scraper platform to match existing skip tracing API format.

---

## API Endpoints

### 1. Search by Name
```http
POST /skip-tracing/search/by-name?name=John+Smith&page=1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "PeopleDetails": [
      {
        "Person ID": "peo_13035550100",
        "Telephone": "+1-303-555-0100",
        "Age": 45,
        "address_region": "CO",
        "postal_code": "80201",
        "city": "Denver",
        "phone": "+1-303-555-0100",
        "phone_number": "+1-303-555-0100"
      }
    ],
    "Status": 200
  }
}
```

---

### 2. Search by Name + Address
```http
POST /skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO+80201
```

**Use Case:** More accurate matching when location is known.

---

### 3. Search by Email
```http
POST /skip-tracing/search/by-email?email=john@example.com
```

**Use Case:** Enriching leads with email data.

---

### 4. Search by Phone
```http
POST /skip-tracing/search/by-phone?phone=%2B1-303-555-0100
```

**Use Case:** Reverse phone lookup.

---

### 5. Get Person Details
```http
GET /skip-tracing/details/peo_13035550100
```

**Response:**
```json
{
  "success": true,
  "data": {
    "All Phone Details": [
      {
        "phone_number": "+1-303-555-0100",
        "phone_type": "Wireless",
        "last_reported": "2026-01-01T00:00:00Z"
      },
      {
        "phone_number": "+1-303-555-0200",
        "phone_type": "Landline",
        "last_reported": null
      }
    ],
    "Person Details": [
      {
        "Age": 45,
        "Telephone": "+1-303-555-0100",
        "Name": "John Smith"
      }
    ],
    "Current Address Details List": [
      {
        "address_region": "CO",
        "postal_code": "80201",
        "city": "Denver",
        "full_address": "123 Main St, Denver, CO 80201"
      }
    ],
    "Email Addresses": [
      "john@example.com",
      "john.smith@work.com"
    ]
  }
}
```

---

## Integration with Your Enrichment System

### Python Client
```python
import httpx

class SkipTracingClient:
    def __init__(self, base_url: str = "http://scraper:8000"):
        self.client = httpx.Client(base_url=base_url, timeout=60.0)
    
    def search_by_name(self, name: str, page: int = 1):
        """Search by name - most common method"""
        response = self.client.post(
            "/skip-tracing/search/by-name",
            params={"name": name, "page": page}
        )
        return response.json()
    
    def search_by_name_and_address(self, name: str, citystatezip: str):
        """Search with location - more accurate"""
        response = self.client.post(
            "/skip-tracing/search/by-name-address",
            params={"name": name, "citystatezip": citystatezip}
        )
        return response.json()
    
    def get_person_details(self, peo_id: str):
        """Get detailed info by Person ID"""
        response = self.client.get(f"/skip-tracing/details/{peo_id}")
        return response.json()

# Usage
client = SkipTracingClient()

# Step 1: Search
results = client.search_by_name("John Smith")
person_id = results["data"]["PeopleDetails"][0]["Person ID"]

# Step 2: Get details
details = client.get_person_details(person_id)
phones = details["data"]["All Phone Details"]
emails = details["data"]["Email Addresses"]
```

---

## Configuration: People Search Sites

### Supported Sites (Examples)
1. **FastPeopleSearch** (free, no auth)
2. **WhitePages** (requires account)
3. **TruePeopleSearch** (free, no auth)
4. **Spokeo** (paid, requires API key)

### Site-Specific Job Templates

Create job templates for each site in your database:

```python
# FastPeopleSearch template
{
    "site": "fastpeoplesearch",
    "base_url": "https://www.fastpeoplesearch.com",
    "search_types": {
        "by_name": {
            "url_pattern": "/name/{name}",
            "fields": {
                "person_id": {"css": ".result-item", "attr": "data-person-id"},
                "name": {"css": ".result-name"},
                "phone": {"css": ".result-phone", "field_type": "phone"},
                "age": {"css": ".result-age", "field_type": "integer"},
                "city": {"css": ".result-city"},
                "state": {"css": ".result-state"},
                "zip_code": {"css": ".result-zip", "field_type": "zip_code"}
            }
        },
        "details": {
            "url_pattern": "/person/{person_id}",
            "fields": {
                "all_phones": {"css": ".phone-list .phone", "field_type": "phone", "all": true},
                "phone_types": {"css": ".phone-list .phone-type", "all": true},
                "all_emails": {"css": ".email-list .email", "field_type": "email", "all": true},
                "address": {"css": ".current-address", "field_type": "address"}
            }
        }
    }
}
```

---

## Field Mapping

### Scraper Fields → Skip Tracing Format

| Scraper Field | Skip Tracing Field | Type | Required |
|---------------|-------------------|------|----------|
| `phone` / `phone_number` / `telephone` | `Telephone` | phone | Yes |
| `person_id` (generated) | `Person ID` | string | Yes |
| `age` | `Age` | integer | No |
| `state` / `address_region` | `address_region` | string | No |
| `zip_code` / `postal_code` | `postal_code` | string | No |
| `city` | `city` | string | No |

### SmartFields Integration

The skip tracing adapter automatically benefits from SmartFields:

```python
# Phone normalization
phone = "+1-303-555-0100"  # Normalized via SmartFields (E164)
phone_type = "Wireless"    # Detected via multi-source consensus

# Email validation
email = "john@example.com"  # Validated via SmartFields
confidence = 0.95           # High confidence = valid email

# Address parsing
address = "123 Main St, Denver, CO 80201"
parsed = {
    "city": "Denver",
    "state": "CO",
    "zip": "80201"
}
```

---

## Two-Step Enrichment Process

### Your Current Workflow:
1. **Search** → Get Person ID + basic info
2. **Details Lookup** → Get all phones, emails, addresses

### Implementation:
```python
def enrich_person(name: str, location: Optional[str] = None):
    """Full enrichment: search + details"""
    
    # Step 1: Search
    if location:
        results = client.search_by_name_and_address(name, location)
    else:
        results = client.search_by_name(name)
    
    if not results["success"]:
        return {"error": "Search failed"}
    
    people = results["data"]["PeopleDetails"]
    if not people:
        return {"error": "No results found"}
    
    # Step 2: Get details for first match
    person_id = people[0]["Person ID"]
    details = client.get_person_details(person_id)
    
    return {
        "basic": people[0],
        "detailed": details["data"]
    }
```

---

## Error Handling

```python
try:
    results = client.search_by_name("John Smith")
except httpx.TimeoutException:
    # Scraper timeout (60s default)
    return {"success": False, "error": "timeout"}
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        # Person not found
        return {"success": False, "error": "not_found"}
    elif e.response.status_code == 500:
        # Scraper failed
        return {"success": False, "error": "scraper_failed"}
```

---

## Performance

### Scraper vs RapidAPI

| Method | RapidAPI Cost | Scraper Cost | Time |
|--------|---------------|--------------|------|
| Search by Name | $0.01-0.02 | $0 | 5-10s |
| Search by Name+Address | $0.02-0.03 | $0 | 5-10s |
| Details Lookup | $0.03-0.05 | $0 | 10-15s |
| **Total (2-step)** | **$0.04-0.07** | **$0** | **15-25s** |

### Optimization Tips

1. **Cache results** (Person ID → details) for 24 hours
2. **Batch searches** when possible
3. **Use name+address** for better accuracy (reduces false positives)
4. **Fallback to RapidAPI** if scraper confidence < 0.75

---

## Testing

```bash
# Health check
curl http://localhost:8000/skip-tracing/health

# Search by name
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=John+Smith&page=1"

# Search with address
curl -X POST "http://localhost:8000/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO+80201"

# Get details
curl "http://localhost:8000/skip-tracing/details/peo_13035550100"
```

---

## Deployment

### Docker Compose
```yaml
services:
  skip-tracing-adapter:
    build: ./scraper-platform
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends_on:
      - postgres
      - redis
      - celery-worker
```

### Environment Variables
```bash
# Scraper
DATABASE_URL=postgresql://user:pass@localhost:5432/scraper
REDIS_URL=redis://localhost:6379/0

# Skip Tracing (optional)
SKIP_TRACING_DEFAULT_SITE=fastpeoplesearch
SKIP_TRACING_TIMEOUT=60
```

---

## Next Steps

1. **Configure people search sites** (add site-specific selectors)
2. **Test with real searches** (verify data quality)
3. **Integrate with enrichment system** (replace RapidAPI calls)
4. **Monitor performance** (track success rate, confidence scores)
5. **Add caching layer** (reduce duplicate lookups)

---

## Cost Savings Estimate

If you currently do:
- 10,000 searches/month @ $0.02 = $200
- 5,000 detail lookups/month @ $0.04 = $200
- **Total: $400/month**

With scraper:
- 10,000 searches @ $0 = $0
- 5,000 detail lookups @ $0 = $0
- **Total: $0/month (just compute)**

**Savings: $400/month = $4,800/year**
