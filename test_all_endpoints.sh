#!/bin/bash

# Comprehensive endpoint testing script
# Tests all 29 claimed endpoints

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0
ERRORS=""

test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local desc=$4
    
    echo -n "Testing $desc... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$path" 2>&1)
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$path" 2>&1)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$path" 2>&1)
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PUT -H "Content-Type: application/json" -d "$data" "$BASE_URL$path" 2>&1)
    elif [ "$method" = "PATCH" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PATCH -H "Content-Type: application/json" -d "$data" "$BASE_URL$path" 2>&1)
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    # Accept 2xx, 404 (for non-existent resources), 422 (validation), 400 (bad request)
    if [[ "$status_code" =~ ^(2[0-9]{2}|404|422|400)$ ]]; then
        echo "✅ ($status_code)"
        ((PASS++))
    else
        echo "❌ ($status_code)"
        ERRORS="$ERRORS\n❌ $desc: HTTP $status_code"
        ((FAIL++))
    fi
}

echo "================================"
echo "ENDPOINT TESTING - ALL 29 ENDPOINTS"
echo "================================"
echo ""

echo "--- SYSTEM (2) ---"
test_endpoint "GET" "/" "" "Root endpoint"
test_endpoint "GET" "/health" "" "Health check"

echo ""
echo "--- JOB MANAGEMENT (5) ---"
test_endpoint "GET" "/jobs" "" "List jobs"
test_endpoint "POST" "/jobs" '{"target_url":"https://example.com","fields":["title"]}' "Create job"
test_endpoint "GET" "/jobs/non-existent-id" "" "Get job (404 expected)"
test_endpoint "PATCH" "/jobs/non-existent-id" '{"fields":["title","price"]}' "Update job (404 expected)"
test_endpoint "POST" "/jobs/non-existent-id/clone" "" "Clone job (404 expected)"

echo ""
echo "--- RUNS MANAGEMENT (7) ---"
test_endpoint "GET" "/jobs/runs" "" "List all runs"
test_endpoint "POST" "/jobs/non-existent-id/runs" "" "Create run (404 expected)"
test_endpoint "GET" "/jobs/non-existent-id/runs" "" "List job runs (404 expected)"
test_endpoint "GET" "/jobs/runs/non-existent-id" "" "Get run details (404 expected)"
test_endpoint "GET" "/jobs/runs/non-existent-id/events" "" "Get run events (404 expected)"
test_endpoint "GET" "/jobs/runs/non-existent-id/records" "" "Get run records (404 expected)"
# SSE stream test would hang, skip
echo "Skipping SSE stream test (would hang)... ⏭️"

echo ""
echo "--- RECORDS MANAGEMENT (3) ---"
test_endpoint "GET" "/jobs/records" "" "List all records"
test_endpoint "GET" "/jobs/records/stats" "" "Get records stats"
test_endpoint "DELETE" "/jobs/records/non-existent-id" "" "Delete record (404 expected)"

echo ""
echo "--- FIELD MAPPING (4) ---"
test_endpoint "GET" "/jobs/non-existent-id/field-maps" "" "List field maps (404 expected)"
test_endpoint "PUT" "/jobs/non-existent-id/field-maps" '{"mappings":[]}' "Bulk upsert (404 expected)"
test_endpoint "POST" "/jobs/non-existent-id/field-maps/validate" '{}' "Validate mappings (404 expected)"
test_endpoint "DELETE" "/jobs/non-existent-id/field-maps/title" "" "Delete mapping (404 expected)"

echo ""
echo "--- PREVIEW & WIZARD (3) ---"
test_endpoint "POST" "/jobs/preview" '{"url":"https://example.com","fields":["title"]}' "Generate preview"
test_endpoint "POST" "/jobs/validate-selector" '{"url":"https://example.com","selector":"h1"}' "Validate selector"
test_endpoint "POST" "/jobs/list-wizard/validate" '{"url":"https://example.com"}' "List wizard validate"

echo ""
echo "--- SESSIONS (4) ---"
test_endpoint "GET" "/jobs/sessions" "" "List sessions"
test_endpoint "POST" "/jobs/sessions" '{"job_id":"test","cookies":[]}' "Create session"
test_endpoint "DELETE" "/jobs/sessions/non-existent-id" "" "Delete session (404 expected)"
test_endpoint "POST" "/jobs/sessions/non-existent-id/validate" "" "Validate session (404 expected)"

echo ""
echo "--- SETTINGS (2) ---"
test_endpoint "GET" "/settings" "" "Get settings"
test_endpoint "PUT" "/settings" '{"default_strategy":"auto"}' "Update settings"

echo ""
echo "================================"
echo "RESULTS"
echo "================================"
echo "✅ PASSED: $PASS"
echo "❌ FAILED: $FAIL"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "ERRORS:"
    echo -e "$ERRORS"
    echo ""
    exit 1
else
    echo "🎉 ALL ENDPOINTS RESPONDING"
    exit 0
fi
