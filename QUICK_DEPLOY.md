# ⚡ Quick Deploy to Railway - Get Real Data in 5 Minutes

## What This Does

Deploys the scraper to Railway so you can test with **REAL DATA** from FastPeopleSearch and TruePeopleSearch.

## Prerequisites

- Railway account (free): https://railway.app
- That's it!

## Option 1: Automated Script (Easiest) ⭐

Just run this one command:

```bash
cd /Users/linkpellow/SCRAPER
./deploy_railway.sh
```

This script will:
1. ✅ Install Railway CLI if needed
2. ✅ Log you in (opens browser)
3. ✅ Create project
4. ✅ Add PostgreSQL database
5. ✅ Add Redis
6. ✅ Set all environment variables
7. ✅ Deploy the scraper
8. ✅ Give you the live URL

**Time: 5 minutes**

## Option 2: Manual Steps

If you prefer to do it manually:

### Step 1: Install Railway CLI

```bash
# Option A: Homebrew (Mac)
brew install railway

# Option B: npm
npm install -g @railway/cli

# Option C: Direct download
bash <(curl -fsSL cli.railway.app/install.sh)
```

### Step 2: Login

```bash
railway login
```

### Step 3: Deploy

```bash
cd /Users/linkpellow/SCRAPER

# Initialize project
railway init

# Add databases
railway add --database postgresql
railway add --database redis

# Set environment variables
railway variables set PYTHONPATH=/app
railway variables set APP_DEFAULT_MAX_ATTEMPTS=3
railway variables set APP_HTTP_TIMEOUT_SECONDS=20
railway variables set APP_BROWSER_NAV_TIMEOUT_MS=30000
railway variables set SCRAPINGBEE_API_KEY=LKC89BNO7ZBOVKLFIAKYK4YE57QSE86O7N2XWOACU2W6ZW2O2Y1M7U326H4YX04438NN9W2WC5R8AI69

# Deploy
railway up

# Get URL
railway domain
```

**Time: 5-7 minutes**

## What Happens During Deployment

```
1. Railway builds your app (2-3 min)
   ✓ Installs Python dependencies
   ✓ Installs Playwright & Chromium
   ✓ Sets up environment

2. Railway runs migrations (10-20 sec)
   ✓ Creates database tables
   ✓ Sets up schema

3. Railway starts your API (10 sec)
   ✓ Health check passes
   ✓ API goes live

🎉 You're live!
```

## Testing Your Deployment

Once deployed, Railway gives you a URL like: `scraper-platform.railway.app`

### Test 1: Health Check

```bash
curl https://your-scraper.railway.app/skip-tracing/health
```

Expected:
```json
{"status":"healthy","service":"skip_tracing_adapter"}
```

### Test 2: Real Enrichment with REAL DATA

```bash
curl -X POST "https://your-scraper.railway.app/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO"
```

**Wait 30-60 seconds** for the scraper to:
1. Search FastPeopleSearch.com
2. Extract real data
3. Return results

Expected response with REAL data:
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

### Test 3: Full Enrichment Flow

```bash
# Step 1: Search
RESPONSE=$(curl -s -X POST "https://your-scraper.railway.app/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO")

# Step 2: Get Person ID
PERSON_ID=$(echo $RESPONSE | jq -r '.data.PeopleDetails[0]."Person ID"')

# Step 3: Get full details
curl "https://your-scraper.railway.app/skip-tracing/details/$PERSON_ID"
```

This gets you:
- ✅ All phone numbers (with types)
- ✅ All email addresses
- ✅ Complete address
- ✅ Age and personal info

## Connecting to BrainScraper

Once deployed, add to your BrainScraper.io environment variables:

```bash
SCRAPER_API_URL=https://your-scraper.railway.app
```

Then BrainScraper can call the scraper API to enrich leads!

## Monitoring

View logs in real-time:

```bash
railway logs --follow
```

View metrics in Railway dashboard:
- https://railway.app/project/your-project

## Cost

Railway free tier includes:
- ✅ $5 credit per month
- ✅ 500 execution hours
- ✅ Shared resources

This scraper uses minimal resources:
- **Estimated cost:** $0-5/month (likely free)
- **Break-even vs RapidAPI:** After 100 enrichments

## Troubleshooting

### Deployment Failed

Check build logs:
```bash
railway logs --build
```

Common issues:
- Playwright installation timeout → Fixed automatically by Railway
- Database connection → Railway sets DATABASE_URL automatically
- Redis connection → Railway sets REDIS_URL automatically

### API Returns Errors

Check runtime logs:
```bash
railway logs
```

### Health Check Fails

Wait 2-3 minutes after deployment. Playwright installation can take time.

### No Results from Search

The scraper is working but FastPeopleSearch may not have data for that person. Try different names/locations.

## Next Steps

After deployment:

1. ✅ Test with real names (people you know)
2. ✅ Verify data quality
3. ✅ Connect BrainScraper to scraper
4. ✅ Test full workflow: LinkedIn → BrainScraper → Scraper → Enriched Data

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Check `DEPLOY_TO_RAILWAY.md` for detailed steps

---

**Ready to deploy?**

```bash
./deploy_railway.sh
```

**That's it! You'll have REAL skip tracing in 5 minutes!** 🚀
