#!/bin/bash
set -e

# Activate venv
. /opt/venv/bin/activate

# Transform DATABASE_URL to psycopg dialect
export APP_DATABASE_URL=$(echo $DATABASE_URL | sed 's|^postgresql://|postgresql+psycopg://|')
export APP_REDIS_URL=$REDIS_URL
export APP_CELERY_BROKER_URL=$REDIS_URL
export APP_CELERY_RESULT_BACKEND=$REDIS_URL

# Run migrations
alembic upgrade head

# Start Celery worker in background (normal pool - Scrapy runs in subprocess)
echo "Starting Celery worker..."
celery -A app.celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!
echo "Celery worker started with PID $CELERY_PID"

# Give Celery a moment to start
sleep 3

# Start Uvicorn in foreground
echo "Starting Uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
