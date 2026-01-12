#!/bin/bash
# Run HITL Pause Architecture Database Migrations

set -e

echo "========================================"
echo "HITL Pause Architecture - DB Migrations"
echo "========================================"
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set"
    echo "Please set it:"
    echo "  export DATABASE_URL='postgresql://user:pass@localhost:5432/scraper_db'"
    exit 1
fi

echo "📦 Database: $DATABASE_URL"
echo ""

# Run migration
echo "🔄 Running migration..."
psql "$DATABASE_URL" -f migrations/001_hitl_pause_architecture.sql

echo ""
echo "✅ Migrations complete!"
echo ""
echo "Next steps:"
echo "1. Restart backend: ./start_backend.sh"
echo "2. Restart Celery worker"
echo "3. Test pause flow: curl -X POST 'http://localhost:8000/skip-tracing/search/by-name?name=Test+Person'"
