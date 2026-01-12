#!/bin/bash
# Quick start script for lead enrichment testing

set -e

echo "=================================="
echo "🚀 Lead Enrichment Test Setup"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: Must run from SCRAPER directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo "📋 Step 1: Checking prerequisites..."

if ! command_exists docker; then
    echo "❌ Docker not found"
    echo "   Please install Docker Desktop"
    exit 1
fi

if ! command_exists python3; then
    echo "❌ Python 3 not found"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Step 2: Check Docker daemon
echo "🐳 Step 2: Checking Docker..."

if ! docker info >/dev/null 2>&1; then
    echo "⚠️  Docker daemon not running"
    echo ""
    echo "Please start Docker Desktop and run this script again."
    echo ""
    echo "Or use demo mode without Docker:"
    echo "  python3 demo_enrichment_flow.py"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Step 3: Start services
echo "🗄️  Step 3: Starting PostgreSQL and Redis..."

docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check PostgreSQL
MAX_RETRIES=30
RETRY=0
while ! docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; do
    RETRY=$((RETRY+1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
    echo "   Waiting for PostgreSQL... ($RETRY/$MAX_RETRIES)"
    sleep 1
done

echo "✅ PostgreSQL ready"

# Check Redis
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis ready"
else
    echo "❌ Redis failed to start"
    exit 1
fi

echo ""

# Step 4: Setup Python environment
echo "🐍 Step 4: Setting up Python environment..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✅ Python environment ready"
echo ""

# Step 5: Run migrations
echo "🔄 Step 5: Running database migrations..."

export PYTHONPATH="$(pwd):$PYTHONPATH"

if alembic upgrade head >/dev/null 2>&1; then
    echo "✅ Migrations complete"
else
    echo "⚠️  Migrations failed (might be already up to date)"
fi

echo ""

# Step 6: Start backend (in background)
echo "🚀 Step 6: Starting backend API..."

# Kill any existing uvicorn process
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# Start backend in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!

echo "   Backend starting (PID: $BACKEND_PID)..."
echo "   Logs: tail -f backend.log"

# Wait for backend to be ready
MAX_RETRIES=30
RETRY=0
while ! curl -s http://localhost:8000/skip-tracing/health >/dev/null 2>&1; do
    RETRY=$((RETRY+1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "❌ Backend failed to start"
        echo "   Check logs: tail backend.log"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    echo "   Waiting for backend... ($RETRY/$MAX_RETRIES)"
    sleep 1
done

echo "✅ Backend API ready"
echo ""

# Step 7: Start Celery worker (in background)
echo "⚙️  Step 7: Starting Celery worker..."

# Kill any existing celery process
pkill -f "celery.*app.celery_app" 2>/dev/null || true

# Start worker in background
nohup celery -A app.celery_app worker --loglevel=info > worker.log 2>&1 &
WORKER_PID=$!

echo "   Worker starting (PID: $WORKER_PID)..."
echo "   Logs: tail -f worker.log"

# Give worker time to start
sleep 3

echo "✅ Celery worker ready"
echo ""

# Step 8: Save PIDs
echo "$BACKEND_PID" > .backend.pid
echo "$WORKER_PID" > .worker.pid

# Step 9: Run test
echo "=================================="
echo "🎯 All services ready!"
echo "=================================="
echo ""
echo "Backend API:    http://localhost:8000"
echo "Health Check:   http://localhost:8000/skip-tracing/health"
echo "API Docs:       http://localhost:8000/docs"
echo ""
echo "Processes:"
echo "  Backend PID:  $BACKEND_PID (logs: backend.log)"
echo "  Worker PID:   $WORKER_PID (logs: worker.log)"
echo ""
echo "=================================="
echo "🧪 Running enrichment test..."
echo "=================================="
echo ""

# Run the demo
python3 demo_enrichment_flow.py "John Smith" "Denver" "CO"

echo ""
echo "=================================="
echo "✨ Test complete!"
echo "=================================="
echo ""
echo "To run more tests:"
echo "  python3 demo_enrichment_flow.py \"Name\" \"City\" \"State\""
echo "  python3 test_lead_enrichment.py"
echo ""
echo "To stop services:"
echo "  ./stop_enrichment_test.sh"
echo ""
echo "Or manually:"
echo "  kill $BACKEND_PID $WORKER_PID"
echo "  docker-compose down"
echo ""
