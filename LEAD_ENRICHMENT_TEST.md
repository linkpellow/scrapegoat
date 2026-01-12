# Lead Enrichment Test - Skip Tracing Integration

## Overview

This demonstrates the complete lead enrichment flow using the skip tracing API. Starting with just a **name, city, and state**, the system enriches the lead with:

- 📱 **Multiple phone numbers** (with types: Wireless/Landline/VoIP)
- 📧 **Email addresses**
- 🎂 **Age**
- 🏠 **Full address with ZIP code**
- 🆔 **Person ID** for tracking

## How It Works

### Two-Step Enrichment Process

```
Initial Lead               Step 1: Search         Step 2: Details           Complete Profile
━━━━━━━━━━━━              ━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━━          ━━━━━━━━━━━━━━
Name: John Smith     →    Find by name       →   Get full details    →    Name: John Smith
City: Denver              + location              for best match          Age: 45
State: CO                                                                  Phone: (303) 555-1234
                                                                          Phone: (720) 555-5678
                                                                          Email: john@example.com
                                                                          Address: 123 Main St
                                                                          City: Denver, CO 80201
```

### Step-by-Step Flow

1. **Initial Data**
   - Input: Name, City, State
   - Missing: Phone, Email, Age, Address details

2. **Search by Name + Location**
   ```
   POST /skip-tracing/search/by-name-address
   ```
   - Searches FastPeopleSearch.com (free, no API key needed)
   - Falls back to TruePeopleSearch.com if needed
   - Returns list of potential matches
   - Each match includes: Person ID, Phone, Age, City, State, ZIP

3. **Get Detailed Information**
   ```
   GET /skip-tracing/details/{person_id}
   ```
   - Fetches comprehensive data for the best match
   - Returns:
     - All phone numbers with types
     - All email addresses
     - Complete address information
     - Personal details

4. **Complete Enriched Profile**
   - All available data merged into single profile
   - Ready for use in your application

## Files

### Test Scripts

1. **`demo_enrichment_flow.py`** ⭐ **START HERE**
   - Works in MOCK mode (no services needed)
   - Shows complete enrichment flow
   - Automatically switches to real API if services running
   - Best for understanding the concept

2. **`test_lead_enrichment.py`**
   - Full integration test
   - Requires backend services running
   - Tests multiple leads
   - Saves results to JSON

### Documentation

- **`START_SERVICES.md`** - How to start PostgreSQL, Redis, and backend
- **`LEAD_ENRICHMENT_TEST.md`** - This file

## Quick Start

### Option 1: Demo Mode (No Setup Required) ⭐

Run the demo in mock mode to see how enrichment works:

```bash
cd /Users/linkpellow/SCRAPER
python3 demo_enrichment_flow.py
```

Or with custom lead:

```bash
python3 demo_enrichment_flow.py "John Smith" "Denver" "CO"
```

This shows the complete flow with example data, no backend needed!

### Option 2: Real API Test (Full Setup)

1. **Start Services** (see `START_SERVICES.md` for details)

   ```bash
   # Option A: Docker (easiest)
   docker-compose up -d
   
   # Option B: Homebrew
   brew services start postgresql@16
   brew services start redis
   ```

2. **Set up Python environment**

   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   ```

3. **Start Backend** (Terminal 1)

   ```bash
   ./start_backend.sh
   ```

4. **Start Worker** (Terminal 2)

   ```bash
   ./start_worker.sh
   ```

5. **Run Tests**

   ```bash
   # Demo (auto-detects real API)
   python3 demo_enrichment_flow.py
   
   # Full test suite
   python3 test_lead_enrichment.py
   
   # Custom lead
   python3 test_lead_enrichment.py "Jane Doe" "Los Angeles" "CA"
   ```

## API Endpoints

### 1. Search by Name + Address

```bash
POST /skip-tracing/search/by-name-address
```

**Parameters:**
- `name` (required): Full name (e.g., "John Smith")
- `citystatezip` (required): Location (e.g., "Denver, CO" or "Denver, CO 80201")

**Example:**

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO"
```

**Response:**

```json
{
  "success": true,
  "data": {
    "PeopleDetails": [
      {
        "Person ID": "peo_3035551234",
        "Telephone": "(303) 555-1234",
        "Age": 45,
        "city": "Denver",
        "address_region": "CO",
        "postal_code": "80201"
      }
    ],
    "Status": 200,
    "_source": "fastpeoplesearch"
  }
}
```

### 2. Get Person Details

```bash
GET /skip-tracing/details/{person_id}
```

**Parameters:**
- `person_id` (path): Person ID from search results

**Example:**

```bash
curl "http://localhost:8000/skip-tracing/details/peo_3035551234"
```

**Response:**

```json
{
  "success": true,
  "data": {
    "All Phone Details": [
      {
        "phone_number": "(303) 555-1234",
        "phone_type": "Wireless"
      },
      {
        "phone_number": "(720) 555-5678",
        "phone_type": "Landline"
      }
    ],
    "Email Addresses": [
      "john.smith@example.com",
      "john@company.com"
    ],
    "Current Address Details List": [
      {
        "full_address": "123 Main St, Denver, CO 80201",
        "city": "Denver",
        "address_region": "CO",
        "postal_code": "80201"
      }
    ],
    "Person Details": [
      {
        "Name": "John Smith",
        "Age": 45,
        "Telephone": "(303) 555-1234"
      }
    ]
  }
}
```

## Example Output

### Demo Mode (Mock Data)

```
======================================================================
🚀 LEAD ENRICHMENT DEMONSTRATION
======================================================================

----------------------------------------------------------------------
📝 STEP 1: Initial Lead Data
----------------------------------------------------------------------

Starting with limited information:
  • Name:  Jane Doe
  • City:  Los Angeles
  • State: CA

❌ Missing: phone, email, age, full address, etc.

----------------------------------------------------------------------
🔍 STEP 2: Search by Name + Location
----------------------------------------------------------------------

Simulating: POST /skip-tracing/search/by-name-address
  name: Jane Doe
  citystatezip: Los Angeles, CA

This would search:
  ✓ FastPeopleSearch.com (free)
  ✓ TruePeopleSearch.com (free, fallback)

----------------------------------------------------------------------
📊 STEP 3: Initial Enrichment Results
----------------------------------------------------------------------

✅ Basic enrichment successful!

New information discovered:
  • Person ID: peo_3035551234
  • Phone:     (303) 555-1234
  • Age:       45
  • ZIP Code:  80201

----------------------------------------------------------------------
📋 STEP 4: Fetch Detailed Information
----------------------------------------------------------------------

Simulating: GET /skip-tracing/details/peo_3035551234

----------------------------------------------------------------------
✨ STEP 5: Complete Enriched Profile
----------------------------------------------------------------------

✅ Complete enrichment successful!

📱 Phone Numbers:
  • (303) 555-1234 (Wireless)
  • (720) 555-5678 (Landline)

📧 Email Addresses:
  • jane.doe@example.com
  • jane@company.com

🏠 Address:
  • 123 Main St, Los Angeles, CA 80201

👤 Personal Info:
  • Name:  Jane Doe
  • Age:   45
  • City:  Los Angeles
  • State: CA
  • ZIP:   80201

======================================================================
📈 ENRICHMENT SUMMARY
======================================================================

Before Enrichment:
  ✓ Name
  ✓ City
  ✓ State
  ✗ Phone
  ✗ Email
  ✗ Age
  ✗ Full Address
  ✗ ZIP Code

After Enrichment:
  ✓ Name
  ✓ City
  ✓ State
  ✓ Phone (2 numbers)
  ✓ Email (2 addresses)
  ✓ Age
  ✓ Full Address
  ✓ ZIP Code
```

## Integration Example

### Python Client

```python
from test_lead_enrichment import LeadEnricher

# Initialize
enricher = LeadEnricher("http://localhost:8000")

# Enrich a lead
result = enricher.enrich_lead(
    name="John Smith",
    city="Denver",
    state="CO",
    get_details=True
)

# Access enriched data
if result["success"]:
    lead = result["enriched"]
    print(f"Phone: {lead['phone']}")
    print(f"Emails: {lead['emails']}")
    print(f"Address: {lead['full_address']}")
```

### cURL Example

```bash
# Step 1: Search
RESPONSE=$(curl -s -X POST \
  "http://localhost:8000/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO")

# Extract Person ID
PERSON_ID=$(echo $RESPONSE | jq -r '.data.PeopleDetails[0]."Person ID"')

# Step 2: Get Details
curl "http://localhost:8000/skip-tracing/details/$PERSON_ID"
```

## Architecture

### Data Sources

The skip tracing API uses **free public people search sites**:

1. **FastPeopleSearch.com** (Primary)
   - No API key required
   - Fast response times
   - Good data quality

2. **TruePeopleSearch.com** (Fallback)
   - Backup if primary fails
   - Similar data quality
   - No API key required

### Features

- ✅ **SmartFields Integration** - Automatic data extraction and validation
- ✅ **Multi-Source Fallback** - Tries multiple sites automatically
- ✅ **Confidence Filtering** - Only returns high-confidence matches
- ✅ **Phone Type Detection** - Wireless vs Landline vs VoIP
- ✅ **Error Handling** - Graceful degradation on failures
- ✅ **Celery Task Queue** - Async scraping with retry logic

## Troubleshooting

### Services Not Running

**Problem:** API returns "Connection refused"

**Solution:**
```bash
# Check services
docker-compose ps

# Start services
docker-compose up -d

# Or use Homebrew
brew services list
brew services start postgresql@16
brew services start redis
```

### No Results Found

**Problem:** API returns empty results

**Possible Causes:**
1. Name/location too vague
2. Person not in public records
3. Network/scraping issues

**Solutions:**
- Try more specific location (add ZIP code)
- Try alternative name spelling
- Check Celery worker logs for scraping errors

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
export PYTHONPATH="$(pwd):$PYTHONPATH"
source venv/bin/activate
```

## Performance

- **Search by Name + Location:** 30-60 seconds (includes scraping)
- **Get Person Details:** 20-40 seconds (detail page scraping)
- **Total Enrichment Time:** ~60-90 seconds for complete profile

## Privacy & Legal

⚠️ **Important Notes:**

1. This system scrapes **public records** from free people search sites
2. All data is publicly available information
3. Use responsibly and in compliance with:
   - FCRA (Fair Credit Reporting Act)
   - GDPR (if applicable)
   - State privacy laws
   - Terms of service of data sources

4. Not for:
   - Credit decisions
   - Employment screening
   - Tenant screening
   - Any FCRA-regulated purpose

## Next Steps

1. ✅ Run demo mode to understand the flow
2. ✅ Start backend services (see `START_SERVICES.md`)
3. ✅ Test with real API
4. ✅ Integrate into your application
5. ✅ Monitor performance and error rates

## Support

For issues or questions:

1. Check `START_SERVICES.md` for setup help
2. Review API endpoint documentation above
3. Check Celery worker logs: `./start_worker.sh`
4. Review backend logs for errors

---

**Status:** ✅ Fully functional with mock mode for demo
**Last Updated:** 2026-01-12
