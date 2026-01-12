# Deploy Scraper to Railway - Quick Guide

## Step 1: Install Railway CLI

```bash
# Option A: Using npm
npm install -g @railway/cli

# Option B: Using Homebrew (Mac)
brew install railway

# Option C: Using curl
bash <(curl -fsSL cli.railway.app/install.sh)
```

## Step 2: Login to Railway

```bash
railway login
```

This opens your browser - just click "Authorize" and you're done.

## Step 3: Initialize Project

```bash
cd /Users/linkpellow/SCRAPER
railway init
```

Select:
- "Create a new project"
- Name it: "scraper-platform" or similar

## Step 4: Add PostgreSQL

```bash
railway add --database postgresql
```

This creates a PostgreSQL database and sets the `DATABASE_URL` automatically.

## Step 5: Add Redis

```bash
railway add --database redis
```

This creates a Redis instance and sets `REDIS_URL` automatically.

## Step 6: Set Environment Variables

```bash
# Set required environment variables
railway variables set PYTHONPATH=/app
railway variables set APP_DEFAULT_MAX_ATTEMPTS=3
railway variables set APP_HTTP_TIMEOUT_SECONDS=20
railway variables set APP_BROWSER_NAV_TIMEOUT_MS=30000
railway variables set SCRAPINGBEE_API_KEY=LKC89BNO7ZBOVKLFIAKYK4YE57QSE86O7N2XWOACU2W6ZW2O2Y1M7U326H4YX04438NN9W2WC5R8AI69
```

Railway will automatically set:
- `DATABASE_URL` (from PostgreSQL service)
- `PORT` (assigned by Railway)
- Redis URLs (from Redis service)

## Step 7: Deploy

```bash
railway up
```

This:
- ✅ Builds your app
- ✅ Runs database migrations
- ✅ Starts the API server
- ✅ Deploys to Railway

Wait 2-3 minutes for deployment to complete.

## Step 8: Get Your URL

```bash
railway domain
```

This shows your deployment URL, like: `scraper-platform.railway.app`

Or generate a custom domain:

```bash
railway domain generate
```

## Step 9: Add Celery Worker

The web service is running. Now add the worker:

```bash
# Create a new service for the worker
railway service create worker

# Set it to use the same environment
railway link

# Deploy worker
railway up --service worker
```

Or manually in Railway dashboard:
1. Go to your project
2. Click "New Service"
3. Select "From GitHub" or "Empty Service"
4. Set start command: `celery -A app.celery_app worker --loglevel=info --concurrency=2`
5. Link to same PostgreSQL and Redis

## Step 10: Test Deployment

```bash
# Get your URL
URL=$(railway domain)

# Test health check
curl https://$URL/skip-tracing/health

# Expected response:
# {"status":"healthy","service":"skip_tracing_adapter"}
```

## Step 11: Test Real Enrichment

```bash
# Test with real data
curl -X POST "https://$URL/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO"
```

Wait 30-60 seconds for scraping to complete. You should get REAL data!

## Complete One-Liner Deployment

If Railway CLI is installed and you're logged in:

```bash
cd /Users/linkpellow/SCRAPER && \
railway init && \
railway add --database postgresql && \
railway add --database redis && \
railway variables set PYTHONPATH=/app && \
railway variables set APP_DEFAULT_MAX_ATTEMPTS=3 && \
railway variables set APP_HTTP_TIMEOUT_SECONDS=20 && \
railway variables set APP_BROWSER_NAV_TIMEOUT_MS=30000 && \
railway variables set SCRAPINGBEE_API_KEY=LKC89BNO7ZBOVKLFIAKYK4YE57QSE86O7N2XWOACU2W6ZW2O2Y1M7U326H4YX04438NN9W2WC5R8AI69 && \
railway up && \
railway domain
```

## Troubleshooting

### Build Fails

Check build logs:
```bash
railway logs --build
```

### Deployment Fails

Check runtime logs:
```bash
railway logs
```

### Database Connection Error

Verify DATABASE_URL is set:
```bash
railway variables
```

### Playwright Installation Fails

Railway should handle this automatically with nixpacks.toml. If it fails, check logs.

## Monitoring

View logs in real-time:
```bash
railway logs --follow
```

View specific service:
```bash
railway logs --service web
railway logs --service worker
```

## Scaling

Railway automatically scales based on load. For manual control:

```bash
# In Railway dashboard:
# Settings → Resources → Scale instances
```

## Cost

- **Free tier**: 500 hours/month, $5 credit
- **Pro**: $20/month for team, usage-based after that
- Estimated cost for scraper: $5-20/month depending on usage

## Next Steps

After deployment:

1. **Copy deployment URL**
2. **Add to BrainScraper.io environment variables:**
   ```bash
   SCRAPER_API_URL=https://your-scraper.railway.app
   ```
3. **Test integration between BrainScraper → Scraper**
4. **Monitor usage and performance**

---

**Your scraper will be live and ready to handle REAL enrichment requests!** 🚀
