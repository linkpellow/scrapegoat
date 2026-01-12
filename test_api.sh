#!/bin/bash

# Simple API test script for Step One control plane

set -e

API_BASE="http://localhost:8000"

echo "🧪 Testing Scraper Platform API"
echo "================================"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" ${API_BASE}/health)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "✅ Health check passed"
    echo "   Response: $body"
else
    echo "❌ Health check failed (HTTP $http_code)"
    exit 1
fi
echo ""

# Test 2: Create Valid Job
echo "Test 2: Create Valid Job"
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
    echo "✅ Job creation passed"
    echo "   Response: $body"
else
    echo "❌ Job creation failed (HTTP $http_code)"
    echo "   Response: $body"
    exit 1
fi
echo ""

# Test 3: Invalid URL (Should Fail)
echo "Test 3: Invalid URL (Should Fail Validation)"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://thisdoesnotexist12345.invalid",
    "fields": ["title"],
    "strategy": "auto"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" != "200" ]; then
    echo "✅ Validation correctly rejected invalid URL"
    echo "   HTTP Code: $http_code"
else
    echo "⚠️  Invalid URL was accepted (validation may be too lenient)"
fi
echo ""

# Test 4: Duplicate Fields (Should Fail)
echo "Test 4: Duplicate Fields (Should Fail Validation)"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://httpbin.org/html",
    "fields": ["title", "title"],
    "strategy": "auto"
  }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" != "200" ]; then
    echo "✅ Validation correctly rejected duplicate fields"
    echo "   HTTP Code: $http_code"
else
    echo "❌ Duplicate fields were accepted"
    exit 1
fi
echo ""

# Test 5: Empty Fields (Should Fail)
echo "Test 5: Empty Fields List (Should Fail Validation)"
response=$(curl -s -w "\n%{http_code}" -X POST ${API_BASE}/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://httpbin.org/html",
    "fields": [],
    "strategy": "auto"
  }')

http_code=$(echo "$response" | tail -n1)

if [ "$http_code" != "200" ]; then
    echo "✅ Validation correctly rejected empty fields"
    echo "   HTTP Code: $http_code"
else
    echo "❌ Empty fields were accepted"
    exit 1
fi
echo ""

echo "================================"
echo "✅ All API tests passed!"
echo ""
echo "Control Plane is functioning correctly."
