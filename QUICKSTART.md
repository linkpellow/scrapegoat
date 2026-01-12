# Quick Start Guide

## Prerequisites

- Python 3.11+
- Docker Desktop (for PostgreSQL & Redis)
- Git

## 1. Initial Setup

```bash
# Run automated setup
make setup

# Or manually:
./setup.sh
```

This will:
- Start PostgreSQL and Redis in Docker
- Create a virtual environment
- Install all dependencies
- Run database migrations

## 2. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start development server
make start

# Or directly:
uvicorn app.main:app --reload
```

Server runs at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## 3. Create Your First Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com",
    "fields": ["title", "price", "description"],
    "requires_auth": false,
    "frequency": "on_demand",
    "strategy": "auto"
  }'
```

Expected response:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "target_url": "https://example.com",
  "fields": ["title", "price", "description"],
  "requires_auth": false,
  "frequency": "on_demand",
  "strategy": "auto",
  "status": "validated"
}
```

## 4. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy"
}
```

## Common Commands

```bash
# Infrastructure management
make infra-up        # Start databases
make infra-down      # Stop databases
make infra-logs      # View logs

# Database operations
make migrate         # Apply migrations
make migration msg="Add new field"  # Create migration
make db-reset        # Reset database (⚠️  destroys data)

# Development
make start           # Start dev server
make clean           # Clean Python cache
```

## Troubleshooting

### Port Already in Use

If port 5432 or 6379 is already in use:

```bash
# Check what's using the port
lsof -i :5432
lsof -i :6379

# Either stop the conflicting service or edit docker-compose.yml
```

### Database Connection Error

```bash
# Verify containers are running
docker-compose ps

# Check logs
docker-compose logs postgres
docker-compose logs redis

# Restart infrastructure
make db-reset
```

### Module Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

## Next Steps

- Review the [README.md](README.md) for architecture details
- Explore the API documentation at `/docs`
- Check the state machine in `app/enums.py`
- Understand validation logic in `app/services/validator.py`

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```

2. **Make changes to models**
   ```bash
   # After modifying models, create migration
   make migration msg="Describe your changes"
   
   # Apply migration
   make migrate
   ```

3. **Test your changes**
   ```bash
   # Start server
   make start
   
   # Test API endpoint
   curl http://localhost:8000/jobs
   ```

4. **Clean up**
   ```bash
   make clean
   ```

## Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/scraper
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
```

## What's Next?

This is Step One: **The Control Plane**

Future steps will add:
- Worker execution layer (Celery tasks)
- Observability & monitoring
- Web UI for job management
- Scraping engines (Scrapy, Playwright, Zyte)

The foundation is now set. Everything else builds on this canonical job specification.
