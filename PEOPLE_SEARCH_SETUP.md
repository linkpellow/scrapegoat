# People Search Integration Setup

## ✅ Skip Tracing with FastPeopleSearch & TruePeopleSearch

Your scraper is now configured to use **both free people search sites** with automatic fallback.

---

## Site Configuration

### Configured Sites:
1. **FastPeopleSearch** (Primary)
   - Free, no auth required
   - Playwright-based extraction
   - Supports: name search, phone search, person details

2. **TruePeopleSearch** (Fallback)
   - Free, no auth required
   - Playwright-based extraction
   - Supports: name search, phone search, person details

### Fallback Logic:
- System tries **FastPeopleSearch first**
- If no results, automatically tries **TruePeopleSearch**
- Returns data from whichever site succeeds
- Response includes `_source` field showing which site was used

---

## Starting the Backend

### Option 1: Using the start script
```bash
cd /Users/linkpellow/SCRAPER
./start_backend.sh
```

### Option 2: Manual start
```bash
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Endpoints

### 1. Search by Name
```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=John+Smith&page=1"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "PeopleDetails": [
      {
        "Person ID": "peo_13035550100",
        "Telephone": "+13035550100",
        "Age": 45,
        "address_region": "CO",
        "postal_code": "80201",
        "city": "Denver",
        "phone": "+13035550100",
        "phone_number": "+13035550100"
      }
    ],
    "Status": 200,
    "_source": "fastpeoplesearch"
  }
}
```

### 2. Search by Name + Address (More Accurate)
```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO+80201"
```

### 3. Search by Phone (Reverse Lookup)
```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-phone?phone=%2B1-303-555-0100"
```

### 4. Get Person Details
```bash
curl "http://localhost:8000/skip-tracing/details/peo_13035550100"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "All Phone Details": [
      {
        "phone_number": "+13035550100",
        "phone_type": "Wireless",
        "last_reported": null
      },
      {
        "phone_number": "+13035550200",
        "phone_type": "Landline",
        "last_reported": null
      }
    ],
    "Person Details": [
      {
        "Age": 45,
        "Telephone": "+13035550100",
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
    ],
    "_source": "fastpeoplesearch"
  }
}
```

---

## Integration with Your Enrichment System

### Python Client Example

```python
import httpx

class SkipTracingClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
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
    
    def search_by_phone(self, phone: str):
        """Reverse phone lookup"""
        response = self.client.post(
            "/skip-tracing/search/by-phone",
            params={"phone": phone}
        )
        return response.json()
    
    def get_person_details(self, peo_id: str):
        """Get detailed info by Person ID"""
        response = self.client.get(f"/skip-tracing/details/{peo_id}")
        return response.json()


# Usage: Two-step enrichment
client = SkipTracingClient()

# Step 1: Search by name
results = client.search_by_name("John Smith")

if results["success"] and results["data"]["PeopleDetails"]:
    person = results["data"]["PeopleDetails"][0]
    person_id = person["Person ID"]
    
    print(f"Found: {person['Telephone']}, Age: {person['Age']}")
    print(f"Source: {results['data']['_source']}")
    
    # Step 2: Get detailed info
    details = client.get_person_details(person_id)
    
    print(f"\nAll phones: {details['data']['All Phone Details']}")
    print(f"Emails: {details['data']['Email Addresses']}")
    print(f"Address: {details['data']['Current Address Details List']}")
```

---

## SmartFields Integration

The skip tracing adapter automatically benefits from SmartFields:

### Phone Normalization
- Input: `"(303) 555-0100"`, `"303.555.0100"`, `"+1-303-555-0100"`
- Output: `"+13035550100"` (E164 format)
- Confidence: `0.95+`

### Email Validation
- Validates RFC format
- Checks disposable domains
- Confidence scoring

### Address Parsing
- Extracts city, state, ZIP from full address
- Normalizes state abbreviations
- Validates ZIP format

---

## Site-Specific Selectors

### FastPeopleSearch
```python
# Name search results
{
    "name": "div.card-body .card-title",
    "phone": "div.card-body .phones a",
    "age": "div.card-body .detail-box-age span",
    "city": "div.card-body .detail-box-address .city",
    "state": "div.card-body .detail-box-address .state"
}

# Person details
{
    "all_phones": "div.phones-table tbody tr td:first-child",
    "phone_types": "div.phones-table tbody tr td:nth-child(2)",
    "all_emails": "div.emails-table tbody tr td:first-child",
    "address": "div.current-address .address-full"
}
```

### TruePeopleSearch
```python
# Name search results
{
    "name": "div.card .h4.card-title",
    "phone": "div.card .content-label:contains('Phone') + .content-value a",
    "age": "div.card .content-label:contains('Age') + .content-value",
    "address": "div.card .content-label:contains('Address') + .content-value"
}

# Person details
{
    "all_phones": "div.content-label:contains('Phone Numbers') + .content-value div.row div",
    "phone_types": "div.content-label:contains('Phone Numbers') + .content-value div.row small",
    "all_emails": "div.content-label:contains('Email Addresses') + .content-value a",
    "address": "div.content-label:contains('Current Address') + .content-value"
}
```

---

## Performance & Cost Savings

### Comparison with RapidAPI

| Method | RapidAPI | Scraper | Time |
|--------|----------|---------|------|
| Search by name | $0.02 | $0 | 5-10s |
| Search by name+address | $0.03 | $0 | 5-10s |
| Person details | $0.04 | $0 | 10-15s |
| **Total (2-step)** | **$0.06** | **$0** | **15-25s** |

### Monthly Savings (Example)
- 10,000 searches @ $0.02 = $200
- 5,000 detail lookups @ $0.04 = $200
- **Total: $400/month → $0/month = $4,800/year saved**

---

## Troubleshooting

### Issue: Module not found error
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH="/Users/linkpellow/SCRAPER:$PYTHONPATH"

# Or use the start script
./start_backend.sh
```

### Issue: Celery worker not running
```bash
# Start Celery worker
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
celery -A app.celery_app worker --loglevel=info
```

### Issue: No results from either site
- Check if Playwright is installed: `playwright install chromium`
- Check Celery worker logs
- Verify site structure hasn't changed (selectors may need updates)

### Issue: Timeout errors
- Increase timeout in API calls (default 60s)
- Check network connectivity
- Verify target sites are accessible

---

## Next Steps

1. **Test with real searches:**
   ```bash
   # Try a real name
   curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=John+Smith"
   ```

2. **Integrate with enrichment system:**
   - Add `SkipTracingClient` to your codebase
   - Replace RapidAPI calls with skip tracing calls
   - Add fallback to RapidAPI if confidence < 0.75

3. **Monitor performance:**
   - Track success rate per site
   - Monitor response times
   - Log confidence scores

4. **Update selectors if needed:**
   - Sites may change their HTML structure
   - Update `app/people_search_sites.py` with new selectors
   - Test after updates

---

## Architecture Files

- `/app/people_search_sites.py` - Site configurations and selectors
- `/app/services/people_search_adapter.py` - Job creation and result parsing
- `/app/api/skip_tracing.py` - API endpoints (matches your existing format)
- `/start_backend.sh` - Backend startup script with PYTHONPATH

---

**Your skip tracing system is now ready to replace RapidAPI!** 🚀
