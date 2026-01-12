#!/bin/bash

set -e

echo "🚀 Setting up Scraper Platform Control Plane..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start PostgreSQL and Redis
echo "📦 Starting PostgreSQL and Redis..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 5

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
python -m playwright install chromium

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
fi

# Database tables will be created automatically on startup (Step Two uses create_all)

echo "✅ Setup complete!"
echo ""
echo "To start the system:"
echo "  source venv/bin/activate"
echo ""
echo "Terminal 1 - API Server:"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "Terminal 2 - Celery Worker:"
echo "  celery -A app.celery_app.celery_app worker --loglevel=INFO"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
