#!/bin/bash
# Install Playwright browsers (called during Railway build)
set -e

echo "📦 Installing Playwright browsers..."
python -m playwright install --with-deps chromium
echo "✅ Playwright browsers installed"
