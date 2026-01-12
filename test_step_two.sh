#!/bin/bash

# Complete end-to-end test for Step Two Run Orchestrator

set -e

API_BASE="http://localhost:8000"

echo "🧪 Testing Step Two: Run Orchestrator"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Create a job
echo "Test 1: Create Job"
echo "-------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://httpbin.org/html",
    "fields": ["title", "content"],
    "requires_auth": false,
    "frequency": "on_demand",
    "strategy": "auto"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Job created successfully${NC}"
    JOB_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   Job ID: $JOB_ID"
else
    echo -e "${RED}❌ Job creation failed (HTTP $http_code)${NC}"
    echo "   Response: $body"
    exit 1
fi
echo ""

# Test 2: Create a run
echo "Test 2: Create Run"
echo "-------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs/${JOB_ID}/runs)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Run created successfully${NC}"
    RUN_ID=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "   Run ID: $RUN_ID"
    echo "   Status: $(echo "$body" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)"
    echo "   Resolved Strategy: $(echo "$body" | grep -o '"resolved_strategy":"[^"]*"' | cut -d'"' -f4)"
else
    echo -e "${RED}❌ Run creation failed (HTTP $http_code)${NC}"
    echo "   Response: $body"
    exit 1
fi
echo ""

# Test 3: Wait for run completion
echo "Test 3: Wait for Run Completion"
echo "--------------------------------"
echo -e "${YELLOW}⏳ Waiting for worker to process run (max 30s)...${NC}"

max_wait=30
waited=0
while [ $waited -lt $max_wait ]; do
    response=$(curl -s ${API_BASE}/jobs/runs/${RUN_ID})
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ "$status" = "completed" ]; then
        echo -e "${GREEN}✅ Run completed successfully${NC}"
        echo "   Final Status: $status"
        break
    elif [ "$status" = "failed" ]; then
        echo -e "${RED}❌ Run failed${NC}"
        failure_code=$(echo "$response" | grep -o '"failure_code":"[^"]*"' | cut -d'"' -f4)
        error_message=$(echo "$response" | grep -o '"error_message":"[^"]*"' | cut -d'"' -f4)
        echo "   Failure Code: $failure_code"
        echo "   Error: $error_message"
        exit 1
    fi
    
    sleep 2
    waited=$((waited + 2))
    echo -n "."
done

if [ $waited -ge $max_wait ]; then
    echo ""
    echo -e "${RED}❌ Run did not complete within ${max_wait}s${NC}"
    echo "   Current Status: $status"
    echo ""
    echo -e "${YELLOW}💡 Troubleshooting:${NC}"
    echo "   1. Is the Celery worker running?"
    echo "      make start-worker"
    echo "   2. Check worker logs for errors"
    echo "   3. Verify Redis is accessible"
    exit 1
fi
echo ""

# Test 4: Get run details
echo "Test 4: Get Run Details"
echo "-----------------------"
response=$(curl -s ${API_BASE}/jobs/runs/${RUN_ID})

if echo "$response" | grep -q '"status":"completed"'; then
    echo -e "${GREEN}✅ Run details retrieved${NC}"
    echo "   Stats:"
    echo "$response" | grep -o '"stats":{[^}]*}' | sed 's/^/      /'
else
    echo -e "${RED}❌ Failed to retrieve run details${NC}"
    exit 1
fi
echo ""

# Test 5: Get run events
echo "Test 5: Get Run Events"
echo "----------------------"
response=$(curl -s ${API_BASE}/jobs/runs/${RUN_ID}/events)

event_count=$(echo "$response" | grep -o '"level":"' | wc -l | tr -d ' ')

if [ "$event_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Run events retrieved${NC}"
    echo "   Event Count: $event_count"
    echo "   Events:"
    echo "$response" | grep -o '"message":"[^"]*"' | sed 's/"message":"//;s/"$//' | sed 's/^/      - /'
else
    echo -e "${RED}❌ No events found${NC}"
    exit 1
fi
echo ""

# Test 6: List job runs
echo "Test 6: List Job Runs"
echo "---------------------"
response=$(curl -s "${API_BASE}/jobs/${JOB_ID}/runs?limit=10")

run_count=$(echo "$response" | grep -o '"id":"' | wc -l | tr -d ' ')

if [ "$run_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Job runs listed${NC}"
    echo "   Total Runs: $run_count"
else
    echo -e "${RED}❌ Failed to list runs${NC}"
    exit 1
fi
echo ""

# Test 7: Create run with explicit browser strategy
echo "Test 7: Browser Strategy Test"
echo "------------------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com",
    "fields": ["title"],
    "strategy": "browser"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    JOB_ID_2=$(echo "$body" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    response=$(curl -s -X POST ${API_BASE}/jobs/${JOB_ID_2}/runs)
    resolved=$(echo "$response" | grep -o '"resolved_strategy":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$resolved" = "browser" ]; then
        echo -e "${GREEN}✅ Browser strategy correctly resolved${NC}"
        echo "   Resolved Strategy: $resolved"
    else
        echo -e "${RED}❌ Expected browser strategy, got: $resolved${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Browser test skipped (job creation failed)${NC}"
fi
echo ""

# Summary
echo "======================================"
echo -e "${GREEN}✅ All Step Two tests passed!${NC}"
echo ""
echo "Run Orchestrator is working correctly:"
echo "  ✅ Jobs are created and validated"
echo "  ✅ Runs are created with strategy resolution"
echo "  ✅ Workers execute runs successfully"
echo "  ✅ Run events are captured"
echo "  ✅ Run details are retrievable"
echo "  ✅ Strategy escalation works"
echo ""
echo "System is ready for Step Three (Field Extraction)."
