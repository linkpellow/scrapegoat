# Scraper Platform - Step Two: Run Orchestrator

## Overview

Step Two builds on the control plane from Step One and adds the complete **Run Orchestration** layer. This is the execution backbone that everything relies on.

## What's New in Step Two

### Core Features

1. **Run Model** - Immutable run instances with full lifecycle tracking
2. **Strategy Resolution** - Deterministic AUTO → HTTP/BROWSER/API_REPLAY resolution
3. **Queue Dispatch** - Celery + Redis task orchestration
4. **Worker Execution** - HTTP (httpx) and Browser (Playwright) execution
5. **Retry Semantics** - Exponential backoff with strategy escalation
6. **Failure Classification** - Blocked/rate-limited/timeout/network/unknown detection
7. **Run Events** - Database-backed event stream for observability
8. **API Endpoints** - Create runs, inspect status, view events

### State Machine

```
Run: QUEUED → RUNNING → [COMPLETED | FAILED]
```

### Strategy Resolution Logic

```
If requires_auth:
    → BROWSER

If strategy != AUTO:
    → Use explicit strategy

Else (AUTO):
    Probe target with HTTP:
    - If blocked/rate-limited → BROWSER
    - If SPA markers detected → BROWSER
    - Else → HTTP
```

### Retry & Escalation

- **Max Attempts**: 3 (configurable)
- **Backoff**: Exponential (10s → 30s → 90s, capped at 300s)
- **Escalation Path**: `HTTP → BROWSER`, `API_REPLAY → BROWSER`
- **Browser stays Browser** (no downgrade)

### Failure Classification

| Code | Trigger | Action |
|------|---------|--------|
| `blocked` | HTTP 401, 403 | Retry with BROWSER |
| `rate_limited` | HTTP 429 | Retry with backoff + escalation |
| `timeout` | Request timeout | Retry with same strategy |
| `network` | Network error | Retry with backoff |
| `bad_response` | HTTP 4xx/5xx | Record and fail after retries |
| `unknown` | Unhandled exception | Record and fail after retries |

## Architecture

```
┌─────────────┐
│   FastAPI   │  Control Plane (Step One)
│   Job API   │  + Run Orchestration (Step Two)
└──────┬──────┘
       │
       ├─→ POST /jobs → Create Job (validated)
       │
       ├─→ POST /jobs/{id}/runs → Create Run
       │      ↓
       │   Strategy Resolution
       │      ↓
       │   Enqueue to Celery
       │
       ├─→ GET /jobs/runs/{id} → Run status
       │
       └─→ GET /jobs/runs/{id}/events → Event stream

┌──────────────────────────────────────┐
│         Redis (Celery Broker)        │
└──────────────┬───────────────────────┘
               │
        ┌──────▼──────┐
        │   Celery    │
        │   Workers   │
        └──────┬──────┘
               │
       ┌───────┴────────┐
       │                │
   ┌───▼────┐      ┌───▼────┐
   │  HTTP  │      │ Browser│
   │ (httpx)│      │(P.wr't)│
   └────────┘      └────────┘
       │                │
       └────────┬───────┘
                ▼
        ┌───────────────┐
        │  PostgreSQL   │
        │  Runs + Events│
        └───────────────┘
```

## Prerequisites

- Python 3.11+
- Docker (PostgreSQL + Redis)
- Playwright browsers

## Quick Start

### 1. Setup Infrastructure

```bash
# Start databases
docker-compose up -d

# Setup environment (includes Playwright install)
make setup

# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Start Components

**Terminal 1 - API Server:**
```bash
source venv/bin/activate
make start
# or: uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
source venv/bin/activate
make start-worker
# or: celery -A app.celery_app.celery_app worker --loglevel=INFO
```

### 3. Create a Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com",
    "fields": ["title"],
    "strategy": "auto"
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "target_url": "https://example.com",
  "fields": ["title"],
  "requires_auth": false,
  "frequency": "on_demand",
  "strategy": "auto",
  "status": "validated"
}
```

### 4. Create a Run

```bash
JOB_ID="550e8400-e29b-41d4-a716-446655440000"

curl -X POST http://localhost:8000/jobs/$JOB_ID/runs
```

Response:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440111",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "attempt": 1,
  "max_attempts": 3,
  "requested_strategy": "auto",
  "resolved_strategy": "http",
  "failure_code": null,
  "error_message": null,
  "stats": {},
  "created_at": "2026-01-11T12:00:00Z",
  "started_at": null,
  "finished_at": null
}
```

### 5. Check Run Status

```bash
RUN_ID="660e8400-e29b-41d4-a716-446655440111"

curl http://localhost:8000/jobs/runs/$RUN_ID
```

### 6. View Run Events

```bash
curl http://localhost:8000/jobs/runs/$RUN_ID/events
```

Response:
```json
[
  {
    "id": "...",
    "run_id": "660e8400-e29b-41d4-a716-446655440111",
    "level": "info",
    "message": "Run created",
    "meta": {"resolved_strategy": "http"},
    "created_at": "2026-01-11T12:00:00Z"
  },
  {
    "id": "...",
    "run_id": "660e8400-e29b-41d4-a716-446655440111",
    "level": "info",
    "message": "Run started",
    "meta": {"attempt": 1, "strategy": "http"},
    "created_at": "2026-01-11T12:00:01Z"
  },
  {
    "id": "...",
    "run_id": "660e8400-e29b-41d4-a716-446655440111",
    "level": "info",
    "message": "Run completed",
    "meta": {
      "stats": {
        "http_status": 200,
        "content_type": "text/html",
        "content_length": 1256,
        "title": "Example Domain"
      }
    },
    "created_at": "2026-01-11T12:00:03Z"
  }
]
```

## Configuration

Environment variables (`.env`):

```env
# Database
APP_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/scraper

# Redis
APP_REDIS_URL=redis://localhost:6379/0
APP_CELERY_BROKER_URL=redis://localhost:6379/1
APP_CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Run Behavior
APP_DEFAULT_MAX_ATTEMPTS=3
APP_HTTP_TIMEOUT_SECONDS=20
APP_BROWSER_NAV_TIMEOUT_MS=30000
```

## Database Schema

### `runs` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `job_id` | UUID | Foreign key to jobs |
| `status` | String | queued/running/failed/completed |
| `attempt` | Integer | Current attempt number |
| `max_attempts` | Integer | Max retry attempts |
| `requested_strategy` | String | Strategy from job definition |
| `resolved_strategy` | String | Actual strategy used |
| `failure_code` | String | Classification code (if failed) |
| `error_message` | String | Error details (if failed) |
| `stats` | JSONB | Execution metadata |
| `created_at` | Timestamp | Run creation time |
| `started_at` | Timestamp | Execution start time |
| `finished_at` | Timestamp | Execution end time |

### `run_events` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `run_id` | UUID | Foreign key to runs |
| `level` | String | info/warn/error |
| `message` | String | Human-readable message |
| `meta` | JSONB | Structured metadata |
| `created_at` | Timestamp | Event timestamp |

## Worker Architecture

### HTTP Execution (`_http_fetch`)

1. Uses `httpx.Client` with configurable timeout
2. Follows redirects automatically
3. Custom User-Agent header
4. Extracts basic metadata (title, status, content-type)
5. Classifies failures (blocked, rate-limited, bad response)

### Browser Execution (`_browser_fetch`)

1. Uses Playwright Chromium in headless mode
2. Realistic viewport (1280x720)
3. Waits for `domcontentloaded` event
4. Extracts full HTML + title
5. Handles JavaScript-heavy SPAs
6. Classifies anti-bot responses

### Retry Logic

```python
# Exponential backoff
backoff_seconds = min(300, 10 * (3 ** (attempt - 1)))

# Strategy escalation
if current == "http":
    next = "browser"
elif current == "api_replay":
    next = "browser"
else:
    next = current  # browser stays browser
```

## Testing Strategy Resolution

### Example 1: Auto with Working HTTP

```bash
POST /jobs
{
  "target_url": "https://httpbin.org/html",
  "fields": ["title"],
  "strategy": "auto"
}

# Probes target → HTTP 200 → Resolved: HTTP
POST /jobs/{id}/runs
→ resolved_strategy: "http"
```

### Example 2: Auto with Blocked HTTP

```bash
POST /jobs
{
  "target_url": "https://blocked-site.example",
  "fields": ["title"],
  "strategy": "auto"
}

# Probes target → HTTP 403 → Resolved: BROWSER
POST /jobs/{id}/runs
→ resolved_strategy: "browser"
```

### Example 3: Requires Auth

```bash
POST /jobs
{
  "target_url": "https://protected.example",
  "fields": ["data"],
  "requires_auth": true,
  "strategy": "auto"
}

# requires_auth=true → Immediate: BROWSER
POST /jobs/{id}/runs
→ resolved_strategy: "browser"
```

### Example 4: Explicit Strategy

```bash
POST /jobs
{
  "target_url": "https://example.com",
  "fields": ["title"],
  "strategy": "browser"
}

# Explicit strategy → Use as-is
POST /jobs/{id}/runs
→ resolved_strategy: "browser"
```

## What's NOT in Step Two

- **Scrapy Integration** (Step Three+)
- **Field Extraction Logic** (Step Three+)
- **Structured Data Extraction** (Step Three+)
- **Proxy Rotation** (Future)
- **CAPTCHA Solving** (Future)
- **Web UI** (Step Four)

Step Two is the **orchestration backbone**. It doesn't extract structured data yet—that's Step Three. It does prove that the execution layer works end-to-end.

## Monitoring & Observability

### Run Events

Every significant state change is logged to `run_events`:

- Run created
- Run started
- Run completed
- Run failed
- Strategy escalated
- Retry scheduled

### Stats Captured

**HTTP Stats:**
```json
{
  "http_status": 200,
  "content_type": "text/html; charset=utf-8",
  "content_length": 1256,
  "title": "Example Domain"
}
```

**Browser Stats:**
```json
{
  "http_status": 200,
  "content_type": "text/html",
  "content_length": 8642,
  "title": "React App",
  "browser": "playwright-chromium"
}
```

## Troubleshooting

### Worker Not Processing Jobs

```bash
# Check Redis connection
redis-cli ping

# Check Celery worker logs
make start-worker-dev

# Verify task is registered
celery -A app.celery_app.celery_app inspect registered
```

### Playwright Installation Issues

```bash
# Reinstall browsers
python -m playwright install chromium

# Check installed browsers
python -m playwright install --help
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker-compose ps

# Check database URL in .env
cat .env | grep DATABASE_URL

# Test connection
psql postgresql://postgres:postgres@localhost:5432/scraper
```

### Run Stuck in QUEUED

- Worker not running → Start with `make start-worker`
- Redis connection issue → Check `docker-compose logs redis`
- Task not registered → Check imports in `app/workers/tasks.py`

## Next Steps

**Step Three: Field Extraction**
- Scrapy spiders with selectors
- Structured data extraction
- Schema validation against job.fields
- Results storage

**Step Four: Web UI**
- Job dashboard
- Run monitoring
- Real-time updates
- Manual retries

**Step Five: Advanced Features**
- Proxy rotation
- CAPTCHA solving
- Rate limiting
- Cost optimization

---

**Step Two Status: Complete**

The Run Orchestrator is production-ready. Every run is tracked, classified, retried, and escalated deterministically. The execution layer is tool-agnostic and observable. Field extraction is next.
