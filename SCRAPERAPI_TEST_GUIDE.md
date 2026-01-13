# ScraperAPI Minimal Test Guide

## Quick Test After Deployment

After a successful deployment, test ScraperAPI integration with minimal API calls:

### Option 1: Automated Test Script (Recommended)

```bash
# Test on Railway
python test_scraperapi_minimal.py https://scrapegoat-production.up.railway.app

# Test locally
python test_scraperapi_minimal.py http://localhost:8000
```

**What it does:**
1. ✅ Health check (0 API calls)
2. ✅ Check API key status (0 API calls)
3. ✅ Make ONE enrichment request (1 API call - will use ScraperAPI if ScrapingBee fails)
4. ✅ Verify usage tracking (0 API calls)

**Total API calls: 1** (minimal!)

---

### Option 2: Manual Testing

#### Step 1: Check API Key Status (No API calls)

```bash
curl "https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scraperapi"
```

**Expected Response:**
```json
{
  "success": true,
  "provider": "scraperapi",
  "keys": [
    {
      "id": 1,
      "provider": "scraperapi",
      "total_credits": 5000,
      "used_credits": 0,
      "remaining_credits": 5000,
      "is_active": true
    }
  ],
  "summary": {
    "total_keys": 1,
    "active_keys": 1,
    "total_credits": 5000,
    "used_credits": 0,
    "remaining_credits": 5000
  }
}
```

#### Step 2: Make ONE Enrichment Request (1 API call)

```bash
curl -X POST "https://scrapegoat-production.up.railway.app/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO"
```

**This will:**
- Try ScrapingBee first (will fail if out of credits)
- Automatically fallback to ScraperAPI
- Use 1 ScraperAPI credit
- Return enrichment results

#### Step 3: Verify Usage Tracking (No API calls)

```bash
curl "https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scraperapi"
```

**Expected:**
- `used_credits` should increase by 1
- `remaining_credits` should decrease by 1

---

## What to Look For

### ✅ Success Indicators

1. **API Key Registered:**
   - `total_keys: 1` or more
   - `is_active: true`

2. **Enrichment Works:**
   - Response has `"success": true`
   - `PeopleDetails` array contains results

3. **Usage Tracked:**
   - `used_credits` increases after request
   - `remaining_credits` decreases accordingly

### ❌ Common Issues

1. **No API Keys Found:**
   - Check environment variable: `APP_SCRAPERAPI_KEY` (single key) or `APP_SCRAPERAPI_API_KEYS` (multiple)
   - ⚠️ Common mistake: `APP_SCRAPERAPI_API_KEY` (extra "API") won't work!
   - Correct: `APP_SCRAPERAPI_KEY` (no "API" in the middle)
   - Verify key is set in Railway dashboard

2. **Enrichment Fails:**
   - Check Railway logs for errors
   - Verify database migrations ran: `alembic upgrade head`

3. **Usage Not Tracked:**
   - Request may have used free methods (HTTP/Playwright)
   - ScrapingBee may have succeeded (didn't need ScraperAPI)
   - Check logs to see which provider was used

---

## Deployment Fix Applied

**Issue:** Playwright installation failing with GLIBCXX error

**Fix:** Removed `--with-deps` flag from `nixpacks.toml` since dependencies are already installed via `aptPkgs`

**File Changed:** `nixpacks.toml`
- Before: `playwright install --with-deps chromium`
- After: `playwright install chromium`

---

## Next Steps

1. **Redeploy** with the fixed `nixpacks.toml`
2. **Set Environment Variable:**
   ```bash
   # Single key (recommended):
   railway variables set APP_SCRAPERAPI_KEY=4c5be84cded205410592f07e6a7e78dd
   
   # OR multiple keys (comma-separated):
   # railway variables set APP_SCRAPERAPI_API_KEYS=key1,key2,key3
   ```
3. **Run Migration:**
   ```bash
   railway run alembic upgrade head
   ```
4. **Test:**
   ```bash
   python test_scraperapi_minimal.py https://scrapegoat-production.up.railway.app
   ```

---

## Monitoring Usage

Check usage anytime:

```bash
# All providers
curl "https://scrapegoat-production.up.railway.app/api-keys/usage"

# Just ScraperAPI
curl "https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scraperapi"

# Just ScrapingBee
curl "https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scrapingbee"
```

---

**Total Test Cost: 1 ScraperAPI credit** (minimal!)
