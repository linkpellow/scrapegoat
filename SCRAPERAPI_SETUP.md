# ScraperAPI Integration - Free Alternative to ScrapingBee

## ✅ Implementation Complete

ScraperAPI has been integrated as a free fallback when ScrapingBee runs out of credits.

**Your ScraperAPI Key:** `4c5be84cded205410592f07e6a7e78dd`  
**Credits:** 5000 API calls  
**Status:** Ready to use

---

## 🎯 How It Works

### Escalation Flow (Updated)

```
1. HTTP (FREE) → Try first
   ↓ Fails
2. Playwright (FREE) → Try second  
   ↓ Fails
3. ScrapingBee (PAID) → Try third
   ↓ Fails or out of credits
4. ScraperAPI (FREE - 5000 credits) → Fallback
```

**Key Features:**
- ✅ Automatic usage tracking (know exactly how many credits used/remaining)
- ✅ Automatic fallback when ScrapingBee fails
- ✅ Multiple API key support (can add more keys later)
- ✅ Credit monitoring via API endpoint

---

## 🔧 Setup on Railway

### Step 1: Add ScraperAPI Key to Railway

```bash
# Login to Railway
railway login

# Link to your project
railway link

# Set the ScraperAPI key (single key - recommended)
railway variables set APP_SCRAPERAPI_KEY=4c5be84cded205410592f07e6a7e78dd

# OR for multiple keys (comma-separated):
# railway variables set APP_SCRAPERAPI_API_KEYS=key1,key2,key3

# Or set via Railway dashboard:
# Project → Variables → Add Variable
# Name: APP_SCRAPERAPI_KEY (for single key)
# OR: APP_SCRAPERAPI_API_KEYS (for multiple keys, comma-separated)
# Value: 4c5be84cded205410592f07e6a7e78dd
```

### Step 2: Deploy

The migration will run automatically on next deploy, creating the `api_key_usage` table.

Or manually trigger migration:
```bash
railway run alembic upgrade head
```

### Step 3: Verify Setup

```bash
# Check API key usage
curl https://scrapegoat-production.up.railway.app/api-keys/usage

# Expected response:
{
  "success": true,
  "provider": "all",
  "keys": [
    {
      "provider": "scraperapi",
      "key_id": "4c5be84c_...",
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

---

## 📊 Usage Tracking

### Check Credits Remaining

```bash
# Get all API key usage
curl https://scrapegoat-production.up.railway.app/api-keys/usage

# Filter by provider
curl https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scraperapi
```

### Response Format

```json
{
  "success": true,
  "provider": "scraperapi",
  "keys": [
    {
      "provider": "scraperapi",
      "key_id": "4c5be84c_...",
      "total_credits": 5000,
      "used_credits": 123,
      "remaining_credits": 4877,
      "is_active": true,
      "last_used_at": "2026-01-12T16:30:00Z"
    }
  ],
  "summary": {
    "total_keys": 1,
    "active_keys": 1,
    "total_credits": 5000,
    "used_credits": 123,
    "remaining_credits": 4877
  }
}
```

---

## 🔄 How Fallback Works

### Automatic Fallback Logic

1. **ScrapingBee tries first** (if configured)
2. **If ScrapingBee fails** (401, 403, out of credits):
   - System automatically tries ScraperAPI
   - No manual intervention needed
3. **ScraperAPI usage is tracked**:
   - Each request consumes 1 credit
   - Remaining credits updated in real-time
   - Key automatically deactivated when credits exhausted

### Example Flow

```
Request comes in
  ↓
Try HTTP → Blocked
  ↓
Try Playwright → Captcha detected
  ↓
Try ScrapingBee → 401 (out of credits)
  ↓
Try ScraperAPI → ✅ Success!
  ↓
Record usage: 1 credit used (4999 remaining)
```

---

## ➕ Adding More API Keys

### Option 1: Comma-Separated (Single Variable)

```bash
railway variables set APP_SCRAPERAPI_API_KEYS=key1,key2,key3
```

### Option 2: Individual Variables

```bash
railway variables set APP_SCRAPERAPI_KEY_1=4c5be84cded205410592f07e6a7e78dd
railway variables set APP_SCRAPERAPI_KEY_2=another_key_here
```

### Option 3: Via API

```bash
curl -X POST https://scrapegoat-production.up.railway.app/api-keys/register \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "scraperapi",
    "api_key": "new_key_here",
    "total_credits": 5000,
    "description": "Second ScraperAPI key"
  }'
```

**The system will automatically:**
- Rotate between available keys
- Use keys with most remaining credits first
- Skip exhausted keys

---

## 📈 Monitoring

### Check Usage Anytime

```bash
# Via API
curl https://scrapegoat-production.up.railway.app/api-keys/usage

# Via Railway logs (see when keys are used)
railway logs --follow | grep "ScraperAPI"
```

### Usage Tracking Details

- **Each request = 1 credit**
- **Tracked in real-time** (database updated immediately)
- **Automatic deactivation** when credits reach 0
- **Last used timestamp** for each key

---

## 🚨 Alerts

The system will log warnings when:
- ScraperAPI key runs low (< 100 credits)
- ScraperAPI key is exhausted
- No available keys for a provider

Check logs:
```bash
railway logs | grep -i "scraperapi\|api.*key"
```

---

## ✅ Testing

### Test ScraperAPI Integration

```bash
# Test enrichment (will use ScraperAPI if ScrapingBee fails)
curl -X POST "https://scrapegoat-production.up.railway.app/skip-tracing/search/by-name?name=John+Smith&city=Denver&state=CO"

# Check usage after test
curl https://scrapegoat-production.up.railway.app/api-keys/usage?provider=scraperapi
```

---

## 📝 Environment Variables

### Required for ScraperAPI

```bash
APP_SCRAPERAPI_API_KEYS=4c5be84cded205410592f07e6a7e78dd
```

Or individual keys:
```bash
APP_SCRAPERAPI_KEY_1=4c5be84cded205410592f07e6a7e78dd
```

### Optional

```bash
# ScrapingBee (will fallback to ScraperAPI if this fails)
APP_SCRAPINGBEE_API_KEY=your_key_here
```

---

## 🎯 Summary

**What You Get:**
- ✅ 5000 free API calls via ScraperAPI
- ✅ Automatic fallback when ScrapingBee fails
- ✅ Real-time usage tracking
- ✅ Multiple key support
- ✅ Credit monitoring endpoint

**Next Steps:**
1. Set `APP_SCRAPERAPI_API_KEYS` on Railway
2. Deploy (migration runs automatically)
3. Test enrichment - it will use ScraperAPI automatically
4. Monitor usage via `/api-keys/usage` endpoint

**Your system is now ready to use free ScraperAPI credits!** 🚀
