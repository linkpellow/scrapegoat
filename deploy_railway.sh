#!/bin/bash
# Automated Railway Deployment Script

set -e

echo "=================================================="
echo "🚀 Deploying Scraper to Railway"
echo "=================================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    echo ""
    echo "Choose installation method:"
    echo "  1) Homebrew (Mac) - recommended"
    echo "  2) npm (requires Node.js)"
    echo "  3) curl (direct download)"
    echo ""
    read -p "Select option (1-3): " install_option
    
    case $install_option in
        1)
            echo "Installing via Homebrew..."
            brew install railway
            ;;
        2)
            echo "Installing via npm..."
            npm install -g @railway/cli
            ;;
        3)
            echo "Installing via curl..."
            bash <(curl -fsSL cli.railway.app/install.sh)
            ;;
        *)
            echo "Invalid option. Exiting."
            exit 1
            ;;
    esac
fi

echo "✅ Railway CLI installed"
echo ""

# Check if logged in
echo "🔐 Checking Railway authentication..."
if ! railway whoami &> /dev/null; then
    echo "⚠️  Not logged in to Railway"
    echo ""
    echo "Opening browser for login..."
    railway login
    echo ""
    echo "✅ Logged in successfully"
else
    echo "✅ Already logged in as: $(railway whoami)"
fi
echo ""

# Check if project is initialized
echo "📦 Checking project setup..."
if ! railway status &> /dev/null; then
    echo "⚠️  Project not initialized"
    echo ""
    echo "Creating new Railway project..."
    railway init
    echo ""
    echo "✅ Project initialized"
else
    echo "✅ Project already initialized"
fi
echo ""

# Add PostgreSQL if not exists
echo "🗄️  Setting up PostgreSQL..."
if ! railway variables | grep -q "DATABASE_URL"; then
    echo "Adding PostgreSQL database..."
    railway add --database postgres
    echo "✅ PostgreSQL added"
else
    echo "✅ PostgreSQL already configured"
fi
echo ""

# Add Redis if not exists
echo "🔴 Setting up Redis..."
if ! railway variables | grep -q "REDIS_URL"; then
    echo "Adding Redis..."
    railway add --database redis
    echo "✅ Redis added"
else
    echo "✅ Redis already configured"
fi
echo ""

# Set environment variables
echo "🔧 Setting environment variables..."
# Note: Railway provides DATABASE_URL and REDIS_URL automatically
# The start command exports these with APP_ prefix as needed by the app
railway variables set PYTHONPATH=/app
railway variables set APP_DEFAULT_MAX_ATTEMPTS=3
railway variables set APP_HTTP_TIMEOUT_SECONDS=20
railway variables set APP_BROWSER_NAV_TIMEOUT_MS=30000
railway variables set SCRAPINGBEE_API_KEY=LKC89BNO7ZBOVKLFIAKYK4YE57QSE86O7N2XWOACU2W6ZW2O2Y1M7U326H4YX04438NN9W2WC5R8AI69

echo "✅ Environment variables configured"
echo ""
echo "ℹ️  Note: DATABASE_URL and REDIS_URL will be set automatically by Railway"
echo "   The start command maps them to APP_* prefixed variables as needed."
echo ""

# Deploy
echo "=================================================="
echo "🚀 Deploying to Railway..."
echo "=================================================="
echo ""
echo "This will take 2-5 minutes..."
echo ""

railway up

echo ""
echo "✅ Deployment complete!"
echo ""

# Get deployment URL
echo "🌐 Getting deployment URL..."
DEPLOY_URL=$(railway domain 2>/dev/null || echo "")

if [ -z "$DEPLOY_URL" ]; then
    echo "⚠️  No domain assigned yet. Generating one..."
    railway domain generate
    DEPLOY_URL=$(railway domain)
fi

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "=================================================="
echo ""
echo "Your scraper is live at:"
echo "🔗 https://$DEPLOY_URL"
echo ""
echo "Test the health endpoint:"
echo "  curl https://$DEPLOY_URL/skip-tracing/health"
echo ""
echo "API Documentation:"
echo "  https://$DEPLOY_URL/docs"
echo ""
echo "View logs:"
echo "  railway logs --follow"
echo ""
echo "=================================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Test the API:"
echo "   curl -X POST \"https://$DEPLOY_URL/skip-tracing/search/by-name-address?name=John+Smith&citystatezip=Denver,+CO\""
echo ""
echo "2. Add to BrainScraper.io .env:"
echo "   SCRAPER_API_URL=https://$DEPLOY_URL"
echo ""
echo "3. Deploy Celery Worker (optional, for better performance):"
echo "   See DEPLOY_TO_RAILWAY.md Step 9"
echo ""
echo "=================================================="
echo "🎉 Ready to test with REAL DATA!"
echo "=================================================="
