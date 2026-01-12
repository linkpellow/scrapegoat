# 🚀 Quick Start - Running the Servers

**Last Updated:** January 11, 2026

---

## Prerequisites ✅

All dependencies are installed and verified:
- ✓ Docker services (PostgreSQL + Redis) running
- ✓ Python virtual environment with all packages
- ✓ Node.js dependencies installed
- ✓ Playwright Chromium browser installed
- ✓ Database migrations applied (7 tables created)

---

## Starting the System

Open **3 separate terminal windows** and run these commands:

### Terminal 1: Backend API Server 🔧

```bash
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
make start
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Access:**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- OpenAPI Schema: http://localhost:8000/openapi.json

---

### Terminal 2: Celery Worker 🔄

```bash
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
make start-worker
```

**Expected output:**
```
-------------- celery@hostname v5.4.0
---- **** ----- 
--- * ***  * -- Darwin-24.6.0-arm64-arm-64bit
-- * - **** --- 
- ** ---------- [config]
- ** ---------- .> app:         app.celery_app
- ** ---------- .> transport:   redis://localhost:6379/1
- ** ---------- .> results:     redis://localhost:6379/2
*** --- * --- [queues]
 -------------- .> celery           exchange=celery(direct) key=celery

[tasks]
  . app.workers.tasks.execute_run_task
  . app.workers.tasks.preview_extraction_task

celery@hostname ready.
```

---

### Terminal 3: Frontend Web UI 🎨

```bash
cd /Users/linkpellow/SCRAPER
make start-web
```

**Expected output:**
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
event - compiled client and server successfully
```

**Access:**
- Web UI: http://localhost:3000

---

## Quick Health Check 🏥

Once all 3 servers are running, verify they're working:

### 1. Check API Health
```bash
curl http://localhost:8000/
```

### 2. Check API Docs
Open in browser: http://localhost:8000/docs

### 3. Check Web UI
Open in browser: http://localhost:3000

### 4. Check Celery Worker
Look for "celery@hostname ready." in Terminal 2

---

## Testing the System 🧪

### Run API Tests
```bash
# In a 4th terminal
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
make test-api
```

### Run Full Integration Tests
```bash
# Requires all 3 servers running
make test-step-two      # Test orchestration
make test-step-three    # Test Scrapy extraction
make test-step-six      # Test complete API
```

---

## Stopping the System 🛑

### Stop Each Server
In each terminal window, press: `CTRL+C`

### Stop Docker Services (Optional)
```bash
make infra-down
```

### Restart Everything
```bash
# Start Docker services
make infra-up

# Then start the 3 servers again in separate terminals
```

---

## Common Issues & Solutions 🔧

### Port Already in Use

**API Server (8000):**
```bash
lsof -ti:8000 | xargs kill -9
```

**Web UI (3000):**
```bash
lsof -ti:3000 | xargs kill -9
```

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart if needed
make infra-down
make infra-up
sleep 5
```

### Redis Connection Error
```bash
# Check if Redis is running
docker ps | grep redis

# Restart if needed
make infra-down
make infra-up
```

### Celery Worker Not Starting
```bash
# Verify Redis is accessible
source venv/bin/activate
python -c "import redis; r = redis.from_url('redis://localhost:6379/1'); print(r.ping())"
```

### Web UI Not Loading
```bash
# Check if API is running
curl http://localhost:8000/

# Verify .env.local
cat web/.env.local
# Should show: NEXT_PUBLIC_API_BASE=http://localhost:8000
```

---

## Development Workflow 💻

### Typical Development Session

1. **Start infrastructure** (if not running):
   ```bash
   make infra-up
   ```

2. **Start all 3 servers** in separate terminals

3. **Make code changes** - servers auto-reload:
   - API: Uvicorn watches Python files
   - Worker: Celery auto-reloads (may need restart for some changes)
   - Web: Next.js hot-reloads React components

4. **Test changes**:
   - Use Web UI: http://localhost:3000
   - Use API Docs: http://localhost:8000/docs
   - Run test scripts: `make test-api`

5. **View logs**:
   - API: Terminal 1
   - Worker: Terminal 2
   - Web: Terminal 3
   - Docker: `make infra-logs`

---

## API Endpoints 📡

### Jobs
- `GET /jobs` - List all jobs
- `POST /jobs` - Create a new scraping job
- `GET /jobs/{job_id}` - Get job details
- `PUT /jobs/{job_id}` - Update job
- `DELETE /jobs/{job_id}` - Delete job

### Runs
- `POST /jobs/{job_id}/runs` - Start a new run
- `GET /runs/{run_id}` - Get run status
- `GET /runs/{run_id}/records` - Get extracted records

### Field Mapping
- `POST /jobs/{job_id}/field-maps` - Create field mapping
- `GET /jobs/{job_id}/field-maps` - List field mappings

### Preview & Wizard
- `POST /preview` - Preview extraction
- `POST /list-wizard/detect` - Detect list patterns

Full API documentation: http://localhost:8000/docs

---

## Next Steps 🎯

You're ready to start testing! Here's what you can do:

1. **Create your first job** via Web UI or API
2. **Test the preview extraction** feature
3. **Configure field mappings** using CSS selectors
4. **Run a job** and see results
5. **Explore the list wizard** for detecting patterns

---

## System Architecture 🏗️

```
┌─────────────────────────────────────────────────────────┐
│                       Browser                           │
│                    localhost:3000                       │
│                    (Next.js Web UI)                     │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP
                 ▼
┌─────────────────────────────────────────────────────────┐
│                    API Server                           │
│                   localhost:8000                        │
│                  (FastAPI Backend)                      │
└────────┬────────────────────────────────┬───────────────┘
         │                                │
         │ PostgreSQL                     │ Redis
         ▼                                ▼
┌─────────────────────┐        ┌─────────────────────────┐
│    PostgreSQL       │        │     Redis + Celery      │
│  localhost:5432     │        │    localhost:6379       │
│   (Database)        │        │   (Task Queue)          │
└─────────────────────┘        └────────┬────────────────┘
                                        │
                                        ▼
                               ┌─────────────────────────┐
                               │    Celery Worker        │
                               │  (Background Tasks)     │
                               │  - Scrapy              │
                               │  - Playwright          │
                               │  - Data Extraction     │
                               └─────────────────────────┘
```

---

**🎉 Everything is ready! Start the 3 servers and begin testing.**
