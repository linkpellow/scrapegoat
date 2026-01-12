#!/bin/bash
#
# Quick Site Test Script
# 
# Usage: ./quick_site_test.sh <site_name> [name] [city] [state]
# Example: ./quick_site_test.sh thatsthem "Link Pellow" "Dowagiac" "MI"
#

set -e

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"

# Parse arguments
SITE_NAME="${1:-thatsthem}"
NAME="${2:-Link Pellow}"
CITY="${3:-Dowagiac}"
STATE="${4:-MI}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  QUICK SITE TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Site: $SITE_NAME"
echo "  Name: $NAME"
echo "  City: $CITY"
echo "  State: $STATE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if backend is running
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

# Build URL
URL="$BASE_URL/skip-tracing/test/search-specific-site"
URL+="?site_name=$(echo $SITE_NAME | sed 's/ /%20/g')"
URL+="&name=$(echo $NAME | sed 's/ /+/g')"
URL+="&city=$(echo $CITY | sed 's/ /+/g')"
URL+="&state=$(echo $STATE | sed 's/ /+/g')"

echo ""
echo "Sending request..."
echo ""

# Make request
START_TIME=$(date +%s)
RESPONSE=$(curl -s -X POST "$URL")
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Parse response
SUCCESS=$(echo "$RESPONSE" | jq -r '.success // false')
RECORD_COUNT=$(echo "$RESPONSE" | jq -r '.records_count // 0')
ERROR=$(echo "$RESPONSE" | jq -r '.error // ""')

# Display results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$SUCCESS" = "true" ]; then
    echo -e "Status: ${GREEN}✓ SUCCESS${NC}"
    echo "Records Found: $RECORD_COUNT"
    echo "Response Time: ${DURATION}s"
    echo ""
    
    if [ "$RECORD_COUNT" -gt "0" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  SAMPLE RECORD"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "$RESPONSE" | jq '.records[0]' || echo "$RESPONSE" | jq '.'
    fi
else
    echo -e "Status: ${RED}✗ FAILED${NC}"
    echo "Records Found: 0"
    echo "Response Time: ${DURATION}s"
    
    if [ -n "$ERROR" ] && [ "$ERROR" != "null" ]; then
        echo ""
        echo -e "${YELLOW}Error:${NC} $ERROR"
    fi
    
    echo ""
    echo "Full response:"
    echo "$RESPONSE" | jq '.'
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Save detailed response
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="site_test_${SITE_NAME}_${TIMESTAMP}.json"
echo "$RESPONSE" | jq '.' > "$OUTPUT_FILE"
echo "Full response saved to: $OUTPUT_FILE"
echo ""

# Exit code based on success
if [ "$SUCCESS" = "true" ] && [ "$RECORD_COUNT" -gt "0" ]; then
    exit 0
else
    exit 1
fi
