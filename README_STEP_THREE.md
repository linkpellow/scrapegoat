# Scraper Platform - Step Three: Scrapy Engine + Field Mapping

## Overview

Step Three adds the real extraction engine: **Scrapy** with a UI-driven field mapping contract. This is the foundation that your future click-to-map UI will drive.

## What's New in Step Three

### Core Features

1. **Field Mapping Model** - UI-to-engine contract for extraction rules
2. **Records Model** - Normalized output storage (JSON-based)
3. **Preview Service** - Foundation for click-to-map UI
4. **Scrapy Engine** - Generic spider driven by job spec
5. **Extraction Rules** - CSS selectors with attr/regex support
6. **Playwright Fallback** - Snapshot generation for JS-heavy sites
7. **API Endpoints** - Preview pages, retrieve records

### Architecture Flow

```
┌──────────────────┐
│   UI Request     │
│  "Show me this   │
│      page"       │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────┐
│  POST /jobs/preview             │
│  - Fetch page (HTTP or Browser) │
│  - Extract HTML snippet         │
│  - Suggest fields (heuristics)  │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   UI: Click-to-Map              │
│   User clicks element           │
│   → Generate CSS selector       │
│   → Store in FieldMap table     │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  POST /jobs/{id}/runs           │
│  - Load FieldMaps for job       │
│  - Resolve strategy             │
│  - Enqueue to Celery            │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Celery Worker                  │
│  - Run Scrapy spider            │
│  - Extract using FieldMaps      │
│  - Store Records in DB          │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  GET /jobs/runs/{id}/records    │
│  - Return extracted data        │
└─────────────────────────────────┘
```

## Database Schema

### `field_maps` Table

Stores extraction rules for each job field.

```sql
CREATE TABLE field_maps (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    field_name VARCHAR NOT NULL,
    selector_spec JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(job_id, field_name)
);
```

**selector_spec format:**

```json
{
  "css": "div.price",      // CSS selector
  "attr": "href",          // optional: extract attribute instead of text
  "all": true,             // optional: extract all matches (list)
  "regex": "\\d+\\.\\d+"   // optional: regex post-processing
}
```

### `records` Table

Stores extracted data from runs.

```sql
CREATE TABLE records (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**data format:**

```json
{
  "title": "Product Name",
  "price": "99.99",
  "description": "Product description...",
  "url": "https://example.com/product/123"
}
```

## API Endpoints

### POST `/jobs/preview`

Preview a page for field mapping (foundation for click-to-map UI).

**Request:**

```json
{
  "url": "https://example.com/product/123",
  "prefer_browser": false
}
```

**Response:**

```json
{
  "url": "https://example.com/product/123",
  "fetched_via": "http",
  "html_snippet": "<!DOCTYPE html>...",
  "suggestions": [
    {
      "label": "title",
      "css": "h1",
      "confidence": 0.75
    },
    {
      "label": "price",
      "css": "[class*=price]",
      "confidence": 0.45
    }
  ]
}
```

**How it works:**

1. Fetches page via HTTP (or Browser if `prefer_browser=true`)
2. If blocked, automatically escalates to Browser
3. Returns first ~6KB of HTML
4. Provides conservative field suggestions:
   - `title`: h1 or title tag
   - `price`: elements with "price" in class/id
   - More heuristics can be added

**UI Use Case:**

```javascript
// Step 1: Preview page
const preview = await fetch('/jobs/preview', {
  method: 'POST',
  body: JSON.stringify({ url: targetUrl })
});

// Step 2: Show HTML in iframe or viewer
// Step 3: User clicks element
// Step 4: Generate CSS selector from clicked element
// Step 5: Store in FieldMap (next endpoint to be added)
```

### GET `/jobs/runs/{run_id}/records`

Retrieve extracted records from a completed run.

**Request:**

```bash
GET /jobs/runs/{run_id}/records?limit=100
```

**Response:**

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "data": {
      "title": "Product Name",
      "price": "99.99",
      "description": "Product description..."
    },
    "created_at": "2026-01-11T12:00:00Z"
  }
]
```

## Scrapy Engine

### Generic Spider

The platform uses a single generic spider driven by the job specification.

**Key Features:**

- CSS selector-based extraction
- Attribute extraction (href, src, etc.)
- List extraction (all matches)
- Regex post-processing
- Normalized text extraction

**Example Flow:**

```python
# Job definition
fields = ["title", "price", "link"]

# Field mappings
field_maps = {
    "title": {"css": "h1.product-title"},
    "price": {"css": "span.price", "regex": r"\d+\.\d+"},
    "link": {"css": "a.details", "attr": "href"}
}

# Spider extracts
{
    "title": "Product Name",
    "price": "99.99",
    "link": "/product/123"
}
```

### Selector Spec Format

Complete selector specification:

```json
{
  "css": "selector",    // REQUIRED: CSS selector
  "attr": "name",       // OPTIONAL: extract attribute
  "all": false,         // OPTIONAL: extract all matches
  "regex": "pattern"    // OPTIONAL: regex extraction
}
```

**Examples:**

```json
// Extract text from h1
{"css": "h1"}

// Extract href from link
{"css": "a.product-link", "attr": "href"}

// Extract all product links
{"css": "a.product-link", "attr": "href", "all": true}

// Extract price with regex
{"css": "span.price", "regex": "\\d+\\.\\d+"}

// Extract all prices
{"css": "span.price", "regex": "\\d+\\.\\d+", "all": true}
```

## Field Mapping Workflow

### 1. Preview Phase

```bash
# User provides URL
curl -X POST http://localhost:8000/jobs/preview \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/product/123"}'
```

Returns HTML snippet + field suggestions.

### 2. Mapping Phase (Manual for Step Three)

```sql
-- Insert field mapping
INSERT INTO field_maps (job_id, field_name, selector_spec)
VALUES (
  'job-uuid',
  'title',
  '{"css": "h1.product-title"}'::jsonb
);

INSERT INTO field_maps (job_id, field_name, selector_spec)
VALUES (
  'job-uuid',
  'price',
  '{"css": "span.price", "regex": "\\d+\\.\\d+"}'::jsonb
);
```

**Step Four will add API endpoints for this.**

### 3. Execution Phase

```bash
# Create job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com/product/123",
    "fields": ["title", "price"],
    "strategy": "auto"
  }'

# Create run
curl -X POST http://localhost:8000/jobs/{job_id}/runs
```

### 4. Retrieval Phase

```bash
# Get records
curl http://localhost:8000/jobs/runs/{run_id}/records
```

Returns:

```json
[
  {
    "id": "record-uuid",
    "run_id": "run-uuid",
    "data": {
      "title": "Product Name",
      "price": "99.99"
    },
    "created_at": "2026-01-11T12:00:00Z"
  }
]
```

## Worker Execution

### Strategy: HTTP (Scrapy)

```python
# 1. Load field maps from database
field_map = {
    "title": {"css": "h1"},
    "price": {"css": ".price", "regex": r"\d+\.\d+"}
}

# 2. Run Scrapy spider with CrawlerProcess
# Uses temporary JSON feed to avoid Twisted reactor issues

# 3. Load items from JSON
items = [
    {"title": "Product 1", "price": "99.99"},
    {"title": "Product 2", "price": "149.99"}
]

# 4. Store as Records
for item in items:
    db.add(Record(run_id=run_id, data=item))
```

### Strategy: BROWSER (Playwright)

```python
# 1. Fetch page with Playwright
html = browser_snapshot_html(url)

# 2. Extract basic metadata
title = extract_title(html)

# 3. Store record with HTML snippet
record = {
    "title": title,
    "html_snippet": html[:8000]
}

# Note: Full browser DOM extraction comes in Step Four
```

### Strategy: API_REPLAY

Currently executes as HTTP (Scrapy path). Token harvesting comes in later steps.

## Preview Service

### Field Suggestion Heuristics

The preview service provides conservative suggestions:

```python
def _suggest_fields(html: str) -> List[Dict]:
    suggestions = []
    
    # Title from h1
    if soup.select_one("h1"):
        suggestions.append({
            "label": "title",
            "css": "h1",
            "confidence": 0.75
        })
    
    # Document title
    if soup.title:
        suggestions.append({
            "label": "document_title",
            "css": "title",
            "confidence": 0.55
        })
    
    # Price elements
    price_nodes = soup.select("[class*=price], [id*=price]")
    if price_nodes:
        suggestions.append({
            "label": "price",
            "css": "[class*=price]",
            "confidence": 0.45
        })
    
    return suggestions
```

**Deliberately Conservative:**

- No aggressive guessing
- UI click-to-map will provide exact selectors
- These are starting points, not production mappings

### Escalation Logic

```python
try:
    if prefer_browser:
        via, html = _browser_get(url)
    else:
        via, html = _http_get(url)
except RuntimeError:
    # Blocked/rate-limited → escalate to browser
    via, html = _browser_get(url)
```

## Testing

### End-to-End Test

```bash
# 1. Preview a page
curl -X POST http://localhost:8000/jobs/preview \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/html",
    "prefer_browser": false
  }'

# 2. Create job
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://httpbin.org/html",
    "fields": ["title"],
    "strategy": "auto"
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.id')

# 3. Create field mapping (manual SQL for Step Three)
psql $DATABASE_URL -c "
INSERT INTO field_maps (job_id, field_name, selector_spec)
VALUES ('$JOB_ID', 'title', '{\"css\": \"h1\"}'::jsonb)
"

# 4. Create run
RUN_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/$JOB_ID/runs)
RUN_ID=$(echo $RUN_RESPONSE | jq -r '.id')

# 5. Wait for completion
sleep 5

# 6. Get records
curl http://localhost:8000/jobs/runs/$RUN_ID/records
```

Expected output:

```json
[
  {
    "id": "record-uuid",
    "run_id": "run-uuid",
    "data": {
      "title": "Herman Melville - Moby-Dick"
    },
    "created_at": "2026-01-11T12:00:00Z"
  }
]
```

## Default Field Mappings

If no FieldMap exists for a job field, the worker provides safe defaults:

```python
def _load_field_map(db, job_id, job_fields):
    # Load existing mappings
    mappings = db.query(FieldMap).filter_by(job_id=job_id).all()
    
    # Fill in defaults for missing fields
    for field in job_fields:
        if field not in mappings:
            if field == "title":
                # Safe default: try h1
                mappings[field] = {"css": "h1", "all": False}
            else:
                # No selector: returns None
                mappings[field] = {"css": "", "all": False}
    
    return mappings
```

## Scrapy Integration Details

### CrawlerProcess vs CrawlerRunner

Step Three uses **CrawlerProcess** inside Celery workers:

```python
process = CrawlerProcess(settings={
    "LOG_ENABLED": False,
    "ROBOTSTXT_OBEY": False,
    "DOWNLOAD_TIMEOUT": 20,
    "USER_AGENT": "scraper-platform/1.0",
    "FEEDS": {
        "output.json": {
            "format": "json",
            "encoding": "utf8"
        }
    }
})

process.crawl(GenericJobSpider, start_url=url, field_map=mapping)
process.start()  # Blocks until complete
```

**Why CrawlerProcess?**

- Self-contained execution
- FEEDS handle output collection
- Avoids Twisted reactor reuse issues in Celery

**How it works:**

1. Creates temporary directory
2. Runs spider with JSON feed output
3. Loads items from JSON file
4. Stores as Records in PostgreSQL

### Twisted Reactor Considerations

```python
# Safe pattern for Celery workers
def _scrapy_extract(url, field_map):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "items.json")
        
        process = CrawlerProcess(settings={...})
        process.crawl(GenericJobSpider, ...)
        process.start()  # Blocks until done
        
        # Load results
        with open(out_path) as f:
            return json.load(f)
```

## What's Working Now

✅ **Preview endpoint** - Fetch page + suggest fields  
✅ **Field mapping model** - UI-to-engine contract  
✅ **Scrapy execution** - Generic spider with CSS selectors  
✅ **Records storage** - Normalized JSON output  
✅ **Playwright fallback** - Browser snapshot for JS-heavy sites  
✅ **Retry + escalation** - Step Two orchestration intact  
✅ **API endpoints** - Preview + Records retrieval  

## What's Deliberately Deferred

❌ **Click-to-map UI** - Step Four  
❌ **FieldMap API endpoints** - Step Four (manual SQL for now)  
❌ **Unified browser extraction** - Step Four (same selectors in Scrapy + Playwright)  
❌ **List page mode** - Step Four (pagination, item links, deduplication)  
❌ **Selector validation** - Step Four (test selector against snapshot)  
❌ **Streaming logs** - Step Four (SSE for real-time updates)  

## Dependencies Added

```txt
scrapy==2.12.0
parsel==1.9.1
beautifulsoup4==4.12.3
lxml==5.3.0
```

**Why these?**

- **Scrapy**: Industry-standard scraping framework
- **parsel**: CSS/XPath selector library (Scrapy dependency)
- **BeautifulSoup4**: HTML parsing for preview suggestions
- **lxml**: Fast XML/HTML parser (BeautifulSoup backend)

## Configuration

No new configuration needed. Step Two settings still apply:

```env
APP_HTTP_TIMEOUT_SECONDS=20         # Used by Scrapy
APP_BROWSER_NAV_TIMEOUT_MS=30000    # Used by Playwright
```

## Troubleshooting

### Scrapy Not Extracting Data

**Symptom:** Records are empty or missing fields

**Diagnosis:**

```sql
-- Check field mappings
SELECT field_name, selector_spec 
FROM field_maps 
WHERE job_id = 'uuid';

-- Check records
SELECT data 
FROM records 
WHERE run_id = 'uuid';
```

**Common Issues:**

1. **No FieldMap exists** → Worker uses defaults (h1 for title, empty for others)
2. **Selector doesn't match** → Record field is `null`
3. **Selector is wrong** → Use preview to test HTML structure

### Preview Endpoint Fails

**Symptom:** 500 error or blocked response

**Fix:**

```bash
# Try with browser
curl -X POST http://localhost:8000/jobs/preview \
  -d '{"url": "...", "prefer_browser": true}'
```

### Twisted Reactor Error

**Symptom:** `ReactorNotRestartable` error in worker logs

**Fix:**

Ensure using `CrawlerProcess` not `CrawlerRunner`. The current implementation uses `CrawlerProcess` which is safe for Celery.

### Empty Records

**Symptom:** Run completes but no records inserted

**Diagnosis:**

```bash
# Check worker logs
make start-worker-dev

# Check run events
curl http://localhost:8000/jobs/runs/{run_id}/events
```

**Common Causes:**

1. Spider yielded no items (selector doesn't match)
2. Scrapy FEED output file not created
3. JSON parsing error

## Next Steps (Step Four)

### Unified Extraction Engine

Make selectors work in both Scrapy and Playwright:

```python
def extract_with_spec(selector, spec):
    """
    Works with:
    - Scrapy Selector
    - Playwright Page/ElementHandle
    - BeautifulSoup (for preview)
    """
    if isinstance(selector, ScrapySelector):
        return _extract_scrapy(selector, spec)
    elif isinstance(selector, PlaywrightPage):
        return _extract_playwright(selector, spec)
    elif isinstance(selector, BeautifulSoup):
        return _extract_bs4(selector, spec)
```

### Click-to-Map UI

1. Show page in iframe/viewer
2. User clicks element
3. Generate stable CSS selector
4. Validate selector against snapshot
5. Store in FieldMap via API

### List Page Mode

1. Detect item containers
2. Extract item links
3. Paginate automatically
4. Deduplicate URLs
5. Enqueue child runs

### FieldMap API

```bash
# Create mapping
POST /jobs/{job_id}/field-maps
{
  "field_name": "price",
  "selector_spec": {"css": "span.price"}
}

# Update mapping
PUT /jobs/{job_id}/field-maps/{field_name}

# Delete mapping
DELETE /jobs/{job_id}/field-maps/{field_name}

# List mappings
GET /jobs/{job_id}/field-maps
```

---

**Step Three Status: Complete ✅**

The Scrapy engine is running, field mappings work, records are being stored, and the preview foundation is ready for click-to-map UI. Everything is orchestration-safe and cleanly layered.

**Version: 3.0.0-step-three**
