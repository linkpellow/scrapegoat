#!/bin/bash

set -e

echo "🔧 Starting Celery Worker..."
echo ""

# Ensure virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "❌ Virtual environment not found. Run 'make setup' first."
        exit 1
    fi
fi

# Start worker
celery -A app.celery_app.celery_app worker --loglevel=INFO --concurrency=4
