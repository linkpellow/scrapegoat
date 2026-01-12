# Integrating Scraper Platform with brainscraper.io

## Current State
- **brainscraper.io**: Live site using RapidAPI/external APIs for enrichment
- **Scraper Platform**: Local scraping system with skip tracing capabilities

## Integration Goal
Add scraper as a backend service to reduce API costs and increase data coverage.

---

## Architecture Options

### Option 1: Microservice Architecture (Recommended)
Keep scraper as separate backend service, call it like any other API.

```
brainscraper.io (Frontend + API Gateway)
    ↓
┌─────────────────┴────────────────┐
│                                  │
RapidAPI Services          Scraper Platform (NEW)
(existing)                  - Skip Tracing API
                           - People Search
                           - Custom Scrapers
```

**Pros:**
- ✅ No changes to existing codebase
- ✅ Can test/deploy independently
- ✅ Easy rollback if issues
- ✅ Scraper scales independently

**Cons:**
- Requires separate deployment

---

### Option 2: Integrated Backend
Merge scraper code into brainscraper.io backend.

```
brainscraper.io
    ├── Frontend
    ├── API Gateway
    ├── RapidAPI Client (existing)
    └── Scraper Engine (NEW - merged)
```

**Pros:**
- ✅ Single deployment
- ✅ Shared database
- ✅ Simpler infrastructure

**Cons:**
- More complex codebase
- Harder to test independently
- Tighter coupling

---

## Recommended Approach: Microservice (Option 1)

### Step 1: Deploy Scraper Platform

#### A. Docker Deployment (Easiest)

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  # Scraper API
  scraper-api:
    build: .
    image: scraper-platform:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/scraper
      - REDIS_URL=redis://redis:6379/0
      - PYTHONPATH=/app
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    restart: unless-stopped

  # Celery Worker
  scraper-worker:
    build: .
    image: scraper-platform:latest
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/scraper
      - REDIS_URL=redis://redis:6379/0
      - PYTHONPATH=/app
    depends_on:
      - postgres
      - redis
    command: celery -A app.celery_app worker --loglevel=info
    restart: unless-stopped

  # PostgreSQL
  postgres:
    image: postgres:16
    environment:
      - POSTGRES_DB=scraper
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # Redis
  redis:
    image: redis:7
    restart: unless-stopped

  # Nginx (Optional - for SSL)
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - scraper-api
    restart: unless-stopped

volumes:
  postgres_data:
```

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application
COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Deploy:

```bash
# On your server (same as brainscraper.io or separate)
cd /path/to/scraper
docker-compose -f docker-compose.production.yml up -d

# Scraper API now running at:
# http://your-server:8000
```

#### B. Railway/Render/Heroku Deployment

**Railway.app** (Recommended - Simple + Free Tier):

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
cd /Users/linkpellow/SCRAPER
railway init
railway up

# Add services
railway add postgresql
railway add redis

# Set environment variables
railway variables set PYTHONPATH=/app
railway variables set DATABASE_URL=<from railway>
railway variables set REDIS_URL=<from railway>

# Get deployment URL
railway domain
# → scraper-platform.railway.app
```

---

### Step 2: Integrate with brainscraper.io

#### A. Create Scraper Client in brainscraper.io

**Add to your backend** (`lib/scraper-client.ts` or similar):

```typescript
// lib/scraper-client.ts
import axios from 'axios';

const SCRAPER_API_URL = process.env.SCRAPER_API_URL || 'http://localhost:8000';

export class ScraperClient {
  private client = axios.create({
    baseURL: SCRAPER_API_URL,
    timeout: 60000, // 60s for scraping
  });

  // Skip Tracing Methods
  async searchByName(name: string, page: number = 1) {
    const response = await this.client.post('/skip-tracing/search/by-name', null, {
      params: { name, page }
    });
    return response.data;
  }

  async searchByNameAndAddress(name: string, citystatezip: string) {
    const response = await this.client.post('/skip-tracing/search/by-name-address', null, {
      params: { name, citystatezip }
    });
    return response.data;
  }

  async searchByPhone(phone: string) {
    const response = await this.client.post('/skip-tracing/search/by-phone', null, {
      params: { phone }
    });
    return response.data;
  }

  async getPersonDetails(peo_id: string) {
    const response = await this.client.get(`/skip-tracing/details/${peo_id}`);
    return response.data;
  }

  // Health Check
  async health() {
    const response = await this.client.get('/skip-tracing/health');
    return response.data;
  }
}

export const scraperClient = new ScraperClient();
```

#### B. Add Scraper as Data Source Option

**In your API route** (e.g., `/api/enrich/person`):

```typescript
// pages/api/enrich/person.ts
import { scraperClient } from '@/lib/scraper-client';
import { rapidApiClient } from '@/lib/rapidapi-client'; // existing

export default async function handler(req, res) {
  const { name, address, source = 'auto' } = req.body;

  // Option 1: Auto-select (try scraper first, fallback to RapidAPI)
  if (source === 'auto') {
    try {
      // Try scraper first (free)
      const scraperResult = await scraperClient.searchByNameAndAddress(name, address);
      
      if (scraperResult.success && scraperResult.data.PeopleDetails.length > 0) {
        // Scraper succeeded - free!
        return res.json({
          success: true,
          data: scraperResult.data,
          source: 'scraper',
          cost: 0
        });
      }
    } catch (error) {
      console.warn('Scraper failed, falling back to RapidAPI:', error.message);
    }

    // Fallback to RapidAPI
    const rapidResult = await rapidApiClient.searchPerson(name, address);
    return res.json({
      success: true,
      data: rapidResult.data,
      source: 'rapidapi',
      cost: 0.05
    });
  }

  // Option 2: Force scraper
  if (source === 'scraper') {
    const result = await scraperClient.searchByNameAndAddress(name, address);
    return res.json({
      success: result.success,
      data: result.data,
      source: 'scraper',
      cost: 0
    });
  }

  // Option 3: Force RapidAPI
  if (source === 'rapidapi') {
    const result = await rapidApiClient.searchPerson(name, address);
    return res.json({
      success: true,
      data: result.data,
      source: 'rapidapi',
      cost: 0.05
    });
  }
}
```

#### C. Add UI Toggle for Data Source

**In your dashboard** (`components/EnrichmentForm.tsx`):

```tsx
<Select
  label="Data Source"
  value={dataSource}
  onChange={(value) => setDataSource(value)}
>
  <option value="auto">Auto (Scraper → RapidAPI)</option>
  <option value="scraper">Scraper Only (Free)</option>
  <option value="rapidapi">RapidAPI Only ($)</option>
</Select>
```

---

### Step 3: Add Environment Variables

**In brainscraper.io `.env`:**

```bash
# Scraper Platform
SCRAPER_API_URL=https://scraper-platform.railway.app
# or
SCRAPER_API_URL=http://localhost:8000  # for local dev
```

---

### Step 4: Monitor Usage & Costs

**Add cost tracking dashboard:**

```typescript
// lib/usage-tracker.ts
export async function trackEnrichment(source: 'scraper' | 'rapidapi', cost: number) {
  await db.enrichmentLogs.create({
    source,
    cost,
    timestamp: new Date()
  });
}

// Dashboard: Show cost savings
export async function getCostSummary(startDate: Date, endDate: Date) {
  const logs = await db.enrichmentLogs.findMany({
    where: { timestamp: { gte: startDate, lte: endDate } }
  });

  const scraperCount = logs.filter(l => l.source === 'scraper').length;
  const rapidApiCount = logs.filter(l => l.source === 'rapidapi').length;
  const totalCost = logs.reduce((sum, l) => sum + l.cost, 0);
  const savedCost = scraperCount * 0.05; // What you would have paid RapidAPI

  return {
    scraperCount,
    rapidApiCount,
    totalCost,
    savedCost,
    savingsPercent: (savedCost / (totalCost + savedCost)) * 100
  };
}
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Test scraper locally with brainscraper.io
- [ ] Set up production database (PostgreSQL)
- [ ] Set up Redis for Celery
- [ ] Configure environment variables
- [ ] Test CORS settings (allow brainscraper.io origin)

### Deployment
- [ ] Deploy scraper platform (Docker/Railway/etc)
- [ ] Run database migrations
- [ ] Start Celery worker
- [ ] Verify health endpoint
- [ ] Test skip tracing API

### Integration
- [ ] Add scraper client to brainscraper.io
- [ ] Update API routes to use scraper
- [ ] Add UI toggle for data source
- [ ] Add cost tracking
- [ ] Test end-to-end flow

### Monitoring
- [ ] Set up uptime monitoring
- [ ] Set up error logging (Sentry)
- [ ] Monitor Celery queue
- [ ] Track success rates per source
- [ ] Monitor cost savings

---

## Example: Full Integration Flow

### User Flow:
1. User enters name on brainscraper.io
2. Frontend calls `/api/enrich/person` with `source=auto`
3. Backend tries scraper first:
   ```typescript
   const result = await scraperClient.searchByName("John Smith");
   ```
4. Scraper creates job, runs Celery task, returns results
5. If scraper succeeds → return data (cost: $0)
6. If scraper fails → fallback to RapidAPI (cost: $0.05)

### Result:
- **70-90% of requests**: Handled by scraper (free)
- **10-30% of requests**: Fallback to RapidAPI
- **Cost reduction**: 70-90% vs 100% RapidAPI

---

## Security Considerations

### 1. Authentication
Add API key to scraper:

```python
# app/main.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Protect endpoints
@router.post("/skip-tracing/search/by-name", dependencies=[Depends(verify_api_key)])
```

In brainscraper.io:

```typescript
this.client = axios.create({
  baseURL: SCRAPER_API_URL,
  headers: {
    'X-API-Key': process.env.SCRAPER_API_KEY
  }
});
```

### 2. Rate Limiting
Add to scraper API:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/skip-tracing/search/by-name")
@limiter.limit("10/minute")  # 10 requests per minute per IP
async def search_by_name(...):
    ...
```

### 3. CORS
Update scraper to allow brainscraper.io:

```python
# app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://brainscraper.io",
        "https://www.brainscraper.io",
        "http://localhost:3000",  # dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Cost Analysis

### Current (100% RapidAPI):
- 10,000 lookups/month @ $0.05 = **$500/month**

### After Integration (Auto mode):
- 7,000 lookups via scraper @ $0 = **$0**
- 3,000 lookups via RapidAPI @ $0.05 = **$150**
- **Total: $150/month**
- **Savings: $350/month = $4,200/year**

### Scraper Hosting Costs:
- Railway.app: $5-20/month (likely free tier for low volume)
- DigitalOcean: $12/month (2GB Droplet)
- AWS: $10-30/month (t3.small)

**Net savings: $330-345/month = $4,000-4,140/year**

---

## Quick Start Commands

```bash
# 1. Deploy scraper to Railway
cd /Users/linkpellow/SCRAPER
railway init
railway add postgresql
railway add redis
railway up

# 2. Get deployment URL
railway domain
# → https://scraper-platform-production.up.railway.app

# 3. Add to brainscraper.io
# In brainscraper.io .env:
echo "SCRAPER_API_URL=https://scraper-platform-production.up.railway.app" >> .env

# 4. Test
curl https://scraper-platform-production.up.railway.app/skip-tracing/health

# 5. Integrate (add scraper client code shown above)
```

---

## Next Steps

1. **Deploy scraper** (Railway recommended for simplicity)
2. **Add scraper client** to brainscraper.io
3. **Test integration** with auto-fallback
4. **Monitor usage** for 1 week
5. **Analyze cost savings**
6. **Optimize** based on data

---

**Your scraper platform is ready to integrate with brainscraper.io!** 🚀
