#!/bin/bash
# Stop all enrichment test services

echo "=================================="
echo "🛑 Stopping Lead Enrichment Test"
echo "=================================="
echo ""

cd "$(dirname "$0")"

# Stop backend
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo "🛑 Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        # Force kill if still running
        kill -9 $BACKEND_PID 2>/dev/null || true
    fi
    rm .backend.pid
fi

# Kill any remaining uvicorn processes
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "   Cleaned up uvicorn processes"

# Stop worker
if [ -f ".worker.pid" ]; then
    WORKER_PID=$(cat .worker.pid)
    if kill -0 $WORKER_PID 2>/dev/null; then
        echo "🛑 Stopping Celery worker (PID: $WORKER_PID)..."
        kill $WORKER_PID
        sleep 2
        # Force kill if still running
        kill -9 $WORKER_PID 2>/dev/null || true
    fi
    rm .worker.pid
fi

# Kill any remaining celery processes
pkill -f "celery.*app.celery_app" 2>/dev/null && echo "   Cleaned up celery processes"

# Stop Docker services
echo "🐳 Stopping Docker services..."
docker-compose down

echo ""
echo "✅ All services stopped"
echo ""
echo "Logs preserved:"
echo "  backend.log - Backend API logs"
echo "  worker.log  - Celery worker logs"
echo ""
