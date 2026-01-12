#!/bin/bash
#
# Run All Site Tests
# 
# Tests all configured people search sites and generates rankings
#

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_NAME="Link Pellow"
TEST_CITY="Dowagiac"
TEST_STATE="MI"

SITES=(
    "thatsthem"
    "searchpeoplefree"
    "zabasearch"
    "anywho"
    "fastpeoplesearch"
    "truepeoplesearch"
)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌐 PEOPLE SEARCH SITE TESTING - ALL SITES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Testing: $TEST_NAME in $TEST_CITY, $TEST_STATE"
echo "  Sites: ${#SITES[@]}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check backend
echo -n "Checking backend... "
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Please start the backend first:"
    echo "  ./start_backend.sh"
    exit 1
fi

echo ""
echo "Starting tests..."
echo ""

RESULTS_FILE="all_sites_test_$(date +%Y%m%d_%H%M%S).txt"

# Track results
declare -A RESULTS
declare -A TIMES
declare -A COUNTS

for SITE in "${SITES[@]}"; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Testing: ${SITE}${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Build URL
    URL="$BASE_URL/skip-tracing/test/search-specific-site"
    URL+="?site_name=${SITE}"
    URL+="&name=$(echo "$TEST_NAME" | sed 's/ /+/g')"
    URL+="&city=$(echo "$TEST_CITY" | sed 's/ /+/g')"
    URL+="&state=${TEST_STATE}"
    
    # Make request
    START_TIME=$(date +%s)
    RESPONSE=$(curl -s -X POST "$URL" 2>&1)
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    # Parse response
    if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
        SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
        RECORD_COUNT=$(echo "$RESPONSE" | jq -r '.records_count // 0')
        ERROR=$(echo "$RESPONSE" | jq -r '.error // ""')
        
        RESULTS[$SITE]=$SUCCESS
        TIMES[$SITE]=$DURATION
        COUNTS[$SITE]=$RECORD_COUNT
        
        if [ "$SUCCESS" = "true" ] && [ "$RECORD_COUNT" -gt "0" ]; then
            echo -e "  Status: ${GREEN}✓ SUCCESS${NC}"
            echo "  Records: $RECORD_COUNT"
            echo "  Time: ${DURATION}s"
            
            # Show sample data
            SAMPLE=$(echo "$RESPONSE" | jq -r '.records[0] | {name, age, phone, city, state, address}' 2>/dev/null)
            if [ -n "$SAMPLE" ] && [ "$SAMPLE" != "null" ]; then
                echo ""
                echo "  Sample Data:"
                echo "$SAMPLE" | sed 's/^/    /'
            fi
        else
            echo -e "  Status: ${RED}✗ FAILED${NC}"
            echo "  Records: 0"
            echo "  Time: ${DURATION}s"
            
            if [ -n "$ERROR" ] && [ "$ERROR" != "null" ] && [ "$ERROR" != '""' ]; then
                echo -e "  ${YELLOW}Error: $ERROR${NC}"
            fi
        fi
    else
        echo -e "  Status: ${RED}✗ ERROR${NC}"
        echo "  Invalid JSON response"
        RESULTS[$SITE]="false"
        TIMES[$SITE]=$DURATION
        COUNTS[$SITE]=0
    fi
    
    echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for SITE in "${SITES[@]}"; do
    SUCCESS=${RESULTS[$SITE]}
    TIME=${TIMES[$SITE]}
    COUNT=${COUNTS[$SITE]}
    
    if [ "$SUCCESS" = "true" ] && [ "$COUNT" -gt "0" ]; then
        echo -e "  ${GREEN}✓${NC} ${SITE}: ${COUNT} records in ${TIME}s"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "  ${RED}✗${NC} ${SITE}: Failed in ${TIME}s"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Total Tested: ${#SITES[@]}"
echo -e "  ${GREEN}Successful: $SUCCESS_COUNT${NC}"
echo -e "  ${RED}Failed: $FAIL_COUNT${NC}"
echo ""

# Recommendations
if [ $SUCCESS_COUNT -ge 3 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ✨ RECOMMENDATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${GREEN}Great results!${NC} $SUCCESS_COUNT sites working."
    echo ""
    echo "  Next step: Run full comparison for detailed rankings"
    echo "  Command: python test_site_comparison.py"
    echo ""
elif [ $SUCCESS_COUNT -ge 1 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⚠️  RECOMMENDATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${YELLOW}Partial success.${NC} $SUCCESS_COUNT site(s) working."
    echo ""
    echo "  Fix the failed sites before running full comparison."
    echo "  Check: SITE_TESTING_SUMMARY.md for troubleshooting"
    echo ""
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ❌ ACTION REQUIRED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo -e "  ${RED}No sites working.${NC} Check:"
    echo "  1. Backend logs for errors"
    echo "  2. Celery worker is running"
    echo "  3. CSS selectors may need updating"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
