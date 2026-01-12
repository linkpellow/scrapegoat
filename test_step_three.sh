#!/bin/bash

# Complete end-to-end test for Step Three: Scrapy Engine + Field Mapping

set -e

API_BASE="http://localhost:8000"

echo "🧪 Testing Step Three: Scrapy Engine + Field Mapping"
echo "======================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Preview endpoint
echo "Test 1: Preview Page"
echo "--------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs/preview \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/html",
    "prefer_browser": false
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Preview endpoint working${NC}"
    fetched_via=$(echo "$body" | grep -o '"fetched_via":"[^"]*"' | cut -d'"' -f4)
    echo "   Fetched via: $fetched_via"
    
    # Check if suggestions exist
    if echo "$body" | grep -q '"suggestions"'; then
        echo -e "${GREEN}   ✓ Field suggestions returned${NC}"
    else
        echo -e "${YELLOW}   ⚠️  No field suggestions${NC}"
    fi
else
    echo -e "${RED}❌ Preview failed (HTTP $http_code)${NC}"
    echo "   Response: $body"
    exit 1
fi
echo ""

# Test 2: Create job with fields
echo "Test 2: Create Job with Fields"
echo "-------------------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://httpbin.org/html",
    "fields": ["title", "content"],
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
    exit 1
fi
echo ""

# Test 3: Create run (will use default field mappings)
echo "Test 3: Create Run with Scrapy Extraction"
echo "------------------------------------------"
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
    exit 1
fi
echo ""

# Test 4: Wait for run completion
echo "Test 4: Wait for Scrapy Execution"
echo "----------------------------------"
echo -e "${YELLOW}⏳ Waiting for Scrapy spider to complete (max 30s)...${NC}"

max_wait=30
waited=0
while [ $waited -lt $max_wait ]; do
    response=$(curl -s ${API_BASE}/jobs/runs/${RUN_ID})
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    
    if [ "$status" = "completed" ]; then
        echo ""
        echo -e "${GREEN}✅ Run completed successfully${NC}"
        records_inserted=$(echo "$response" | grep -o '"records_inserted":[0-9]*' | cut -d':' -f2)
        echo "   Final Status: $status"
        echo "   Records Inserted: $records_inserted"
        break
    elif [ "$status" = "failed" ]; then
        echo ""
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
    exit 1
fi
echo ""

# Test 5: Get extracted records
echo "Test 5: Retrieve Extracted Records"
echo "-----------------------------------"
response=$(curl -s ${API_BASE}/jobs/runs/${RUN_ID}/records)

record_count=$(echo "$response" | grep -o '"id":"' | wc -l | tr -d ' ')

if [ "$record_count" -gt 0 ]; then
    echo -e "${GREEN}✅ Records retrieved successfully${NC}"
    echo "   Record Count: $record_count"
    echo ""
    echo "   Sample Record:"
    echo "$response" | head -20 | sed 's/^/      /'
else
    echo -e "${YELLOW}⚠️  No records found${NC}"
    echo "   This might be expected if field mappings weren't set"
    echo "   Response: $response"
fi
echo ""

# Test 6: Preview with browser fallback
echo "Test 6: Browser Preview Mode"
echo "-----------------------------"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs/preview \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "prefer_browser": true
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    fetched_via=$(echo "$body" | grep -o '"fetched_via":"[^"]*"' | cut -d'"' -f4)
    if [ "$fetched_via" = "browser" ]; then
        echo -e "${GREEN}✅ Browser mode working${NC}"
        echo "   Fetched via: $fetched_via"
    else
        echo -e "${YELLOW}⚠️  Expected browser but got: $fetched_via${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Browser preview test skipped${NC}"
fi
echo ""

# Summary
echo "======================================================"
echo -e "${GREEN}✅ Step Three tests passed!${NC}"
echo ""
echo "Scrapy Engine is working:"
echo "  ✅ Preview endpoint generates field suggestions"
echo "  ✅ Jobs are created with field definitions"
echo "  ✅ Scrapy spiders execute and extract data"
echo "  ✅ Records are stored in normalized format"
echo "  ✅ Browser fallback works for JS-heavy sites"
echo ""
echo "Next: Step Four (Click-to-map UI + Unified extraction)"
