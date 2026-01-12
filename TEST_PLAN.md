# Complete Testing Plan

## Phase 0: Database Migrations (REQUIRED FIRST)

### Step 1: Set Database URL
```bash
export DATABASE_URL='postgresql://user:pass@localhost:5432/scraper_db'
```

### Step 2: Run Migrations
```bash
cd /Users/linkpellow/SCRAPER
./run_migrations.sh
```

**Expected output:**
```
✅ HITL Pause Architecture migrations complete!
session_vaults columns: domain, health_status, last_validated, intervention_id
domain_configs table: 2 rows (fastpeoplesearch, truepeoplesearch)
waiting_for_human enum: waiting_for_human
```

---

## Phase 1: Service Restart

### Stop All Services
```bash
pkill -f "uvicorn app.main"
pkill -9 -f "celery.*worker"
sleep 2
```

### Start Backend
```bash
cd /Users/linkpellow/SCRAPER
./start_backend.sh &
sleep 5

# Verify
curl -s http://localhost:8000/health | jq '.'
# Expected: {"status": "healthy"}
```

### Start Celery Worker
```bash
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
export PYTHONPATH="$(pwd):$PYTHONPATH"
celery -A app.celery_app worker --loglevel=info &
sleep 3

# Verify in logs
tail -f /tmp/celery.log | grep "celery@"
# Expected: "celery@hostname ready"
```

---

## Phase 2: Test Proactive Session Health Probes

### Test 1: No Session (Should Create Intervention Immediately)

```bash
# Trigger enrichment for domain requiring session
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Test+Person" \
  -H "Content-Type: application/json" | jq '.'
```

**Expected behavior:**
1. Run starts
2. Session probe runs BEFORE execution
3. No session found
4. Intervention created immediately
5. Run paused (no wasted execution)

**Verify:**
```bash
# Check for intervention
curl -s "http://localhost:8000/interventions?status=pending" | jq '.[] | {
  type,
  trigger_reason,
  payload: .payload.probe_result
}'
```

**Expected output:**
```json
{
  "type": "manual_access",
  "trigger_reason": "Session required but not available",
  "payload": "no_session"
}
```

### Test 2: Invalid Session (Should Detect Before Execution)

First, add an invalid session:
```bash
# TODO: Add invalid session to test probe
# For now, skip this test
```

---

## Phase 3: Test Provider Routing

### Check Domain Classification

```bash
# Check FastPeopleSearch classification
curl -s "http://localhost:8000/domains" | jq '.[] | select(.domain == "www.fastpeoplesearch.com")'
```

**Expected (after learning):**
```json
{
  "domain": "www.fastpeoplesearch.com",
  "access_class": "human",
  "requires_session": "required",
  "block_rate_403": 0.95,
  "total_attempts": 5,
  "successful_attempts": 0
}
```

### Test Provider Routing Decision

```bash
# Trigger enrichment (no session)
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Jane+Doe"

# Check logs for routing decision
tail -50 /tmp/celery.log | grep -i "routing\|provider\|skip"
```

**Expected in logs:**
```
Domain classified as INFRA or high-block HUMAN - routing to provider
Skipping direct attempts for www.fastpeoplesearch.com
```

---

## Phase 4: Test Confidence Filtering

### Test 1: Ambiguous Name (Many Results)

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=John+Smith" | jq '{
  success,
  filtered: .data._filtered,
  results_count: (.data.PeopleDetails | length)
}'
```

**Expected:**
```json
{
  "success": true,
  "filtered": 42,
  "results_count": 5
}
```
*Shows that 42 ambiguous results were filtered, returning only top 5*

### Test 2: Specific Name + Location (Better Match)

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name-and-address?name=Robert+Johnson&citystatezip=Denver,+CO" | jq '{
  success,
  filtered: .data._filtered,
  results_count: (.data.PeopleDetails | length)
}'
```

**Expected:**
```json
{
  "success": true,
  "filtered": 0,
  "results_count": 1
}
```
*Specific search yields high-confidence match, no filtering needed*

### Test 3: No Match (Confidence Too Low)

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Zzzzz+Nonexistent" | jq '{
  success,
  results_count: (.data.PeopleDetails | length)
}'
```

**Expected:**
```json
{
  "success": true,
  "results_count": 0
}
```
*No results or low confidence → returns empty instead of creating HITL*

---

## Phase 5: Test Complete Pause/Resume Flow

### Step 1: Trigger Enrichment (Will Pause)

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Test+User" \
  -w "\n%{http_code}\n" | jq '.'
```

### Step 2: Check Run Status

```bash
# Get latest run
RUN_ID=$(curl -s "http://localhost:8000/runs" | jq -r '.[0].id')
echo "Run ID: $RUN_ID"

# Check status
curl -s "http://localhost:8000/runs/$RUN_ID" | jq '{
  status,
  error_message,
  stats: .stats.intervention_id
}'
```

**Expected:**
```json
{
  "status": "waiting_for_human",
  "error_message": "Paused: Session required but not available",
  "stats": "abc-123-intervention-id"
}
```

### Step 3: Get Intervention Details

```bash
# List pending interventions
INTERVENTION_ID=$(curl -s "http://localhost:8000/interventions?status=pending" | jq -r '.[0].id')
echo "Intervention ID: $INTERVENTION_ID"

# Get details
curl -s "http://localhost:8000/interventions/$INTERVENTION_ID" | jq '{
  type,
  trigger_reason,
  priority,
  domain: .payload.domain
}'
```

**Expected:**
```json
{
  "type": "manual_access",
  "trigger_reason": "Session required but not available",
  "priority": "high",
  "domain": "www.fastpeoplesearch.com"
}
```

### Step 4: Capture Session (Manual)

**Option A: Use Cookie-Editor Extension**

1. Install Cookie-Editor: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
2. Visit: https://www.fastpeoplesearch.com
3. Search for: "John Smith"
4. Complete any CAPTCHAs
5. Click Cookie-Editor icon → Export → Copy JSON

**Option B: Mock Session (For Testing)**

```bash
# Create mock session JSON
cat > /tmp/test_session.json <<'EOF'
{
  "cookies": [
    {
      "name": "session_id",
      "value": "test123",
      "domain": ".fastpeoplesearch.com",
      "path": "/",
      "expires": -1,
      "httpOnly": false,
      "secure": true,
      "sameSite": "Lax"
    }
  ],
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
  "captured_method": "manual_export"
}
EOF
```

### Step 5: Resolve Intervention with Session

```bash
# Read session JSON
SESSION_JSON=$(cat /tmp/test_session.json | jq -c '.')

# Resolve intervention
curl -X POST "http://localhost:8000/interventions/$INTERVENTION_ID/resolve" \
  -H "Content-Type: application/json" \
  -d "{
    \"resolution\": {
      \"action\": \"session_captured\",
      \"method\": \"manual_export\"
    },
    \"resolved_by\": \"test@example.com\",
    \"captured_session\": $SESSION_JSON
  }" | jq '.'
```

**Expected response:**
```json
{
  "success": true,
  "message": "Intervention resolved and run resumed",
  "intervention_id": "abc-123",
  "run_id": "def-456",
  "run_status": "queued"
}
```

### Step 6: Verify Auto-Resume

```bash
# Wait 10 seconds for worker to pick up resumed run
sleep 10

# Check run status
curl -s "http://localhost:8000/runs/$RUN_ID" | jq '{
  status,
  stats: .stats.resumed_at
}'
```

**Expected:**
```json
{
  "status": "completed",
  "stats": "2026-01-12T06:15:00Z"
}
```

### Step 7: Verify Session Saved

```bash
# Check SessionVault
curl -s "http://localhost:8000/sessions?domain=www.fastpeoplesearch.com" | jq '.[] | {
  domain,
  health_status,
  is_valid,
  intervention_id
}'
```

**Expected:**
```json
{
  "domain": "www.fastpeoplesearch.com",
  "health_status": "valid",
  "is_valid": true,
  "intervention_id": "abc-123"
}
```

---

## Phase 6: Test Session Reuse (No Intervention Needed)

### Trigger Another Enrichment

```bash
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Jane+Smith"
```

**Expected behavior:**
1. Session probe runs
2. Valid session found
3. Execution proceeds with session
4. SUCCESS (no intervention)

**Verify:**
```bash
# Check latest run
curl -s "http://localhost:8000/runs" | jq '.[0] | {
  status,
  stats: .stats.session_used
}'
```

**Expected:**
```json
{
  "status": "completed",
  "stats": true
}
```

---

## Phase 7: Test SSE Dashboard (Optional)

### Open SSE Stream

```bash
# Terminal 1: Listen to SSE
curl -N http://localhost:8000/events/runs/events
```

### Trigger Enrichment

```bash
# Terminal 2: Trigger job
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Test"
```

**Expected in Terminal 1:**
```
data: {"type": "connected", "timestamp": "2026-01-12T06:00:00Z"}

data: {"type": "run.started", "run_id": "...", "target_url": "..."}

data: {"type": "intervention.created", "intervention_id": "...", "reason": "..."}

data: {"type": "run.completed", "run_id": "...", "status": "completed"}
```

---

## Success Criteria

### ✅ Proactive Session Probes
- [ ] Intervention created BEFORE execution (not during)
- [ ] No wasted scraping attempts with invalid sessions
- [ ] Sessions validated within 3 seconds

### ✅ Provider Routing
- [ ] High-block domains skip direct attempts
- [ ] Provider used immediately when appropriate
- [ ] Domain classification learned after 5+ attempts

### ✅ Confidence Filtering
- [ ] Ambiguous results filtered (>10 matches)
- [ ] Low confidence required fields filtered
- [ ] Response includes `_filtered` count

### ✅ Pause/Resume Flow
- [ ] Run status: `waiting_for_human` when paused
- [ ] Intervention created with correct type/reason
- [ ] Auto-resume after intervention resolution
- [ ] Session saved to SessionVault
- [ ] Future runs use saved session

### ✅ Overall System
- [ ] No 403 terminal failures
- [ ] All pauses are recoverable
- [ ] Domain learning working
- [ ] SSE events flowing

---

## Troubleshooting

### Issue: Migrations Failed
```bash
# Check if enum already exists
psql $DATABASE_URL -c "SELECT enumlabel FROM pg_enum WHERE enumlabel = 'waiting_for_human';"

# If exists, migrations are safe to skip
```

### Issue: Services Won't Start
```bash
# Check ports
lsof -i :8000  # Backend
lsof -i :5432  # Postgres
lsof -i :6379  # Redis

# Check logs
tail -100 /tmp/backend.log
tail -100 /tmp/celery.log
```

### Issue: No Interventions Created
```bash
# Check domain config exists
psql $DATABASE_URL -c "SELECT * FROM domain_configs WHERE domain = 'www.fastpeoplesearch.com';"

# If missing, seed manually:
psql $DATABASE_URL -c "INSERT INTO domain_configs (domain, access_class, requires_session) VALUES ('www.fastpeoplesearch.com', 'human', 'required');"
```

### Issue: Run Stuck in `waiting_for_human`
```bash
# Check intervention exists
curl "http://localhost:8000/interventions?status=pending"

# Manually resolve if needed
curl -X POST "http://localhost:8000/interventions/{id}/resolve" \
  -H "Content-Type: application/json" \
  -d '{"resolution": {"action": "manual"}, "resolved_by": "admin"}'
```

---

## Quick Test Script

```bash
#!/bin/bash
# quick_test.sh - Run all tests

set -e

echo "🧪 Running Complete Test Suite..."

# Phase 0: Check prerequisites
echo "✓ Checking database..."
psql $DATABASE_URL -c "SELECT 1;" > /dev/null || exit 1

# Phase 1: Services
echo "✓ Checking backend..."
curl -sf http://localhost:8000/health > /dev/null || exit 1

# Phase 2: Test enrichment
echo "✓ Testing enrichment..."
RESPONSE=$(curl -sf -X POST "http://localhost:8000/skip-tracing/search/by-name?name=Test")
echo "$RESPONSE" | jq '.success' | grep -q true || exit 1

# Phase 3: Check intervention
echo "✓ Checking interventions..."
INTERVENTIONS=$(curl -sf "http://localhost:8000/interventions?status=pending")
echo "$INTERVENTIONS" | jq 'length' | grep -q "[0-9]" || exit 1

echo ""
echo "✅ All tests passed!"
echo ""
echo "Next steps:"
echo "1. Manually capture session for FastPeopleSearch"
echo "2. Resolve pending intervention"
echo "3. Test auto-resume"
```

Save and run:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

## Summary

**Minimum viable test:**
1. Run migrations
2. Restart services
3. Trigger enrichment → verify pause
4. Check intervention created
5. Resolve with session → verify auto-resume

**Full test:**
- All phases above
- Verify all 3 refinements working
- Test session reuse
- Monitor SSE stream

**Time estimate:**
- Minimum: 15 minutes
- Full: 45 minutes
