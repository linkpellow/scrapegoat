#!/bin/bash
# Quick Test - HITL Pause Architecture
# Tests all core functionality in ~5 minutes

set -e

echo "========================================"
echo "HITL Pause Architecture - Quick Test"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Phase 0: Prerequisites"
echo "------------------------"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL not set${NC}"
    echo "Run: export DATABASE_URL='postgresql://user:pass@localhost:5432/scraper_db'"
    exit 1
fi
echo -e "${GREEN}✓${NC} DATABASE_URL set"

# Check database connection
psql "$DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Database connection OK"
else
    echo -e "${RED}❌ Cannot connect to database${NC}"
    exit 1
fi

# Check if migrations run
ENUM_CHECK=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM pg_enum WHERE enumlabel = 'waiting_for_human';")
if [ "$ENUM_CHECK" -eq "1" ]; then
    echo -e "${GREEN}✓${NC} Migrations already applied"
else
    echo -e "${YELLOW}⚠${NC} Migrations not applied, run: ./run_migrations.sh"
    exit 1
fi

echo ""
echo "🚀 Phase 1: Service Health Checks"
echo "-----------------------------------"

# Check backend
if curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓${NC} Backend running (http://localhost:8000)"
else
    echo -e "${RED}❌ Backend not running${NC}"
    echo "Start with: ./start_backend.sh"
    exit 1
fi

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis running"
else
    echo -e "${YELLOW}⚠${NC} Redis not responding (SSE may not work)"
fi

echo ""
echo "🧪 Phase 2: Test Proactive Session Probe"
echo "------------------------------------------"

# Trigger enrichment (will probe session first)
echo "Triggering enrichment for 'Test Person'..."
RESPONSE=$(curl -sf -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Test+Person" || echo '{"success":false}')
SUCCESS=$(echo "$RESPONSE" | jq -r '.success')

if [ "$SUCCESS" == "true" ]; then
    echo -e "${GREEN}✓${NC} Enrichment API responding"
else
    echo -e "${RED}❌ Enrichment API failed${NC}"
    echo "$RESPONSE" | jq '.'
fi

# Check for intervention
sleep 2
INTERVENTIONS=$(curl -sf "http://localhost:8000/interventions?status=pending" || echo '[]')
INTERVENTION_COUNT=$(echo "$INTERVENTIONS" | jq 'length')

if [ "$INTERVENTION_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓${NC} Intervention created (count: $INTERVENTION_COUNT)"
    
    # Show first intervention
    FIRST_INTERVENTION=$(echo "$INTERVENTIONS" | jq '.[0]')
    INTERVENTION_TYPE=$(echo "$FIRST_INTERVENTION" | jq -r '.type')
    TRIGGER_REASON=$(echo "$FIRST_INTERVENTION" | jq -r '.trigger_reason')
    
    echo "  Type: $INTERVENTION_TYPE"
    echo "  Reason: $TRIGGER_REASON"
else
    echo -e "${YELLOW}⚠${NC} No interventions created (may already have session)"
fi

echo ""
echo "🔍 Phase 3: Test Domain Configuration"
echo "---------------------------------------"

# Check domain configs exist
DOMAIN_COUNT=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM domain_configs;")
if [ "$DOMAIN_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓${NC} Domain configs seeded ($DOMAIN_COUNT domains)"
    
    # Show FastPeopleSearch config
    FPS_CONFIG=$(psql "$DATABASE_URL" -tAc "SELECT access_class, requires_session, block_rate_403 FROM domain_configs WHERE domain = 'www.fastpeoplesearch.com';")
    if [ -n "$FPS_CONFIG" ]; then
        echo "  FastPeopleSearch: $FPS_CONFIG"
    fi
else
    echo -e "${YELLOW}⚠${NC} No domain configs found"
    echo "  System will learn over time, or seed manually"
fi

echo ""
echo "📊 Phase 4: Test Run Status"
echo "----------------------------"

# Get latest run
LATEST_RUN=$(curl -sf "http://localhost:8000/runs" | jq '.[0]' || echo 'null')
if [ "$LATEST_RUN" != "null" ]; then
    RUN_STATUS=$(echo "$LATEST_RUN" | jq -r '.status')
    RUN_ID=$(echo "$LATEST_RUN" | jq -r '.id')
    
    echo -e "${GREEN}✓${NC} Latest run found"
    echo "  Run ID: ${RUN_ID:0:8}..."
    echo "  Status: $RUN_STATUS"
    
    if [ "$RUN_STATUS" == "waiting_for_human" ]; then
        echo -e "${GREEN}✓${NC} Run correctly paused (not failed)"
    elif [ "$RUN_STATUS" == "completed" ]; then
        echo -e "${GREEN}✓${NC} Run completed successfully"
    elif [ "$RUN_STATUS" == "failed" ]; then
        echo -e "${YELLOW}⚠${NC} Run failed (old behavior?)"
    fi
else
    echo -e "${YELLOW}⚠${NC} No runs found"
fi

echo ""
echo "🎯 Phase 5: System Summary"
echo "---------------------------"

# Summary stats
TOTAL_RUNS=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM runs;")
PAUSED_RUNS=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM runs WHERE status = 'waiting_for_human';")
PENDING_INTERVENTIONS=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM intervention_tasks WHERE status = 'pending';")
SESSIONS=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM session_vaults WHERE is_valid = true;")

echo "Total Runs: $TOTAL_RUNS"
echo "Paused Runs: $PAUSED_RUNS"
echo "Pending Interventions: $PENDING_INTERVENTIONS"
echo "Valid Sessions: $SESSIONS"

echo ""
echo "========================================"
echo "✅ Quick Test Complete!"
echo "========================================"
echo ""

if [ "$PENDING_INTERVENTIONS" -gt "0" ]; then
    echo "📌 Next Steps:"
    echo "1. View pending interventions:"
    echo "   curl http://localhost:8000/interventions?status=pending | jq '.'"
    echo ""
    echo "2. Capture session manually:"
    echo "   - Visit https://www.fastpeoplesearch.com"
    echo "   - Search for 'John Smith'"
    echo "   - Export cookies with Cookie-Editor"
    echo ""
    echo "3. Resolve intervention:"
    echo "   curl -X POST http://localhost:8000/interventions/{id}/resolve \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{...session data...}'"
    echo ""
    echo "4. Watch auto-resume:"
    echo "   curl http://localhost:8000/runs | jq '.[0].status'"
fi

if [ "$SESSIONS" -gt "0" ]; then
    echo "✨ You have valid sessions! Try another enrichment:"
    echo "   curl -X POST 'http://localhost:8000/skip-tracing/search/by-name?name=Jane+Doe'"
    echo "   (Should succeed automatically using saved session)"
fi

echo ""
echo "📖 Full test plan: TEST_PLAN.md"
echo "📊 SSE Dashboard: curl -N http://localhost:8000/events/runs/events"
echo ""
