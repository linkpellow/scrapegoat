# Starting Services for Lead Enrichment Test

## Prerequisites

You need PostgreSQL and Redis running to use the skip tracing API.

## Option 1: Docker (Recommended)

### Start Docker Desktop

1. Open Docker Desktop application
2. Wait for it to fully start

### Start Services

```bash
cd /Users/linkpellow/SCRAPER
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379

### Check Services

```bash
docker-compose ps
```

## Option 2: Homebrew (macOS)

### Install Services

```bash
# Install PostgreSQL
brew install postgresql@16

# Install Redis
brew install redis

# Start services
brew services start postgresql@16
brew services start redis
```

### Create Database

```bash
createdb scraper
```

## Option 3: PostgreSQL.app (macOS)

### Download PostgreSQL.app

1. Visit https://postgresapp.com/
2. Download and install
3. Open PostgreSQL.app
4. Click "Initialize" to create a new server
5. Click "Start"

### Install Redis

```bash
brew install redis
brew services start redis
```

## Step 2: Set up Python Environment

```bash
cd /Users/linkpellow/SCRAPER

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Run Database Migrations

```bash
# Activate venv first
source venv/bin/activate

# Run migrations
./run_migrations.sh

# Or manually
alembic upgrade head
```

## Step 4: Start Backend Server

### Terminal 1: Backend API

```bash
./start_backend.sh
```

Or manually:

```bash
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Celery Worker (for scraping tasks)

```bash
./start_worker.sh
```

Or manually:

```bash
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
celery -A app.celery_app worker --loglevel=info
```

## Step 5: Test the Services

### Quick Health Check

```bash
curl http://localhost:8000/skip-tracing/health
```

Expected response:
```json
{"status":"healthy","service":"skip_tracing_adapter"}
```

### Run Lead Enrichment Test

```bash
python test_lead_enrichment.py
```

Or with custom lead:

```bash
python test_lead_enrichment.py "John Smith" "Denver" "CO"
```

## Troubleshooting

### PostgreSQL Connection Error

**Error:** `could not connect to server: Connection refused`

**Solution:**
- Check if PostgreSQL is running: `docker-compose ps` or `brew services list`
- Verify port 5432 is open: `nc -z localhost 5432`
- Check `.env` file has correct DATABASE_URL

### Redis Connection Error

**Error:** `Error 111 connecting to localhost:6379`

**Solution:**
- Check if Redis is running: `redis-cli ping`
- Should return: `PONG`
- If not: `brew services start redis` or `docker-compose up -d redis`

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
```bash
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### Celery Not Processing Jobs

**Error:** Jobs stuck in pending state

**Solution:**
- Make sure Celery worker is running in separate terminal
- Check worker logs for errors
- Verify Redis connection: `redis-cli ping`

## Quick Start (One-liner)

If Docker Desktop is running:

```bash
cd /Users/linkpellow/SCRAPER && \
docker-compose up -d && \
sleep 5 && \
source venv/bin/activate && \
alembic upgrade head && \
./start_backend.sh &
./start_worker.sh &
sleep 3 && \
python test_lead_enrichment.py
```

## Current Status

✅ Redis is running (verified)
❌ PostgreSQL needs to be started
❌ Backend API needs to be started
❌ Celery worker needs to be started
