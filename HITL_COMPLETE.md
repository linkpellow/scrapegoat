# HITL (Human-in-the-Loop) — Enterprise-Grade Implementation ✅

**Date:** 2026-01-11  
**Status:** Production-ready  
**Architecture:** Event-driven, replay-first, deterministic

---

## What Is HITL?

**NOT** manual babysitting like Octoparse.

**IS** a targeted intervention layer where:
- System knows it's uncertain
- Intervention improves future runs
- Actions are auditable and replayable
- Human input generates rules, not patches

---

## Core Principle

> **Humans should only step in when the system triggers intervention based on evidence, not when users decide to "check on things."**

This is **event-driven HITL**, not manual monitoring.

---

## Architecture

```
┌───────────────┐
│ Worker / Run  │  ← Detects low confidence, drift, auth failure, blocks
└───────┬───────┘
        │ creates
        ▼
┌────────────────────┐
│ InterventionTask   │  ← First-class database entity
└───────┬────────────┘
        │ human resolves via
        ▼
┌────────────────────┐
│ HITL API           │  ← UI fetches tasks, submits resolutions
└───────┬────────────┘
        │ applies resolution as
        ▼
┌────────────────────┐
│ Rules (not patches)│  ← Selector versions, normalization rules
└───────┬────────────┘
        │ triggers
        ▼
┌────────────────────┐
│ Auto-Resume        │  ← New run with updated config
└────────────────────┘
```

---

## When HITL Triggers (ONLY 4 Conditions)

### 1. Low-Confidence SmartFields
```python
if field.confidence < 0.75 and field.required:
    create_intervention("field_confirm")
```

**Example:**
- Email field extracts: `"not-an-email"`
- Confidence: 0.1
- Required: true
- → **Intervention created**

### 2. Selector Drift
```python
if selector_hash_changed and extraction_empty:
    create_intervention("selector_fix")
```

**Example:**
- Old selector: `.product-title`
- Extraction: empty
- Page structure changed
- → **Intervention created**

### 3. Auth Expired
```python
if failure == "auth_expired" and job.requires_auth:
    create_intervention("login_refresh")
```

**Example:**
- Run fails with 401
- Job requires auth
- → **Intervention created**

### 4. Persistent Hard Block
```python
if all_engines_failed and block_signals_detected:
    create_intervention("manual_access")
```

**Example:**
- HTTP → 403
- Playwright → captcha detected
- Provider → access denied
- → **Intervention created**

---

## Intervention Types

### Type 1: `selector_fix`
**Trigger:** Selector drift detected  
**Human Action:** Click element to generate new selector  
**System Response:** 
- Creates new selector version
- Preserves old selector in history
- Future runs use new version
- Historical data unchanged

**Example Resolution:**
```json
{
  "new_selector": ".new-product-title",
  "clicked_element": {"tagName": "h1", "className": "new-product-title"}
}
```

### Type 2: `field_confirm`
**Trigger:** Low-confidence field extraction  
**Human Action:** Confirm, edit, or mark "not present"  
**System Response:**
- Confirm → Increase confidence weighting
- Edit → Store normalization override
- Not Present → Mark field as optional

**Example Resolution:**
```json
{
  "action": "edit",
  "value": "john@company.com",
  "normalization_rule": {"lowercase": true, "strip_domain": false}
}
```

### Type 3: `login_refresh`
**Trigger:** Auth expired  
**Human Action:** Log in via Playwright recorder  
**System Response:**
- Saves new session to SessionVault
- Triggers new run with fresh session

**Example Resolution:**
```json
{
  "new_session_id": "abc123",
  "captured_at": "2026-01-11T22:00:00Z"
}
```

### Type 4: `manual_access`
**Trigger:** Persistent hard block  
**Human Action:** Document bypass method or mark site blocked  
**System Response:**
- Logs bypass method
- Optionally disables job
- Adds site to blocklist

**Example Resolution:**
```json
{
  "bypass_method": "use_residential_proxy",
  "notes": "Site blocks datacenter IPs",
  "action": "mark_blocked"
}
```

---

## Database Schema

### `intervention_tasks` Table
```sql
CREATE TABLE intervention_tasks (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL,
    run_id UUID,
    
    type VARCHAR NOT NULL,  -- selector_fix | field_confirm | login_refresh | manual_access
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending | in_progress | completed | expired
    trigger_reason VARCHAR NOT NULL,  -- low_confidence | selector_drift | auth_expired | hard_block
    
    payload JSONB NOT NULL,  -- Context for human
    resolution JSONB,  -- Human decision (structured)
    
    priority VARCHAR NOT NULL DEFAULT 'normal',  -- low | normal | high | critical
    expires_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR
);
```

### `page_snapshots` Table
```sql
CREATE TABLE page_snapshots (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL,
    run_id UUID,
    
    url VARCHAR NOT NULL,
    html_content TEXT NOT NULL,  -- Captured page HTML
    html_size INTEGER NOT NULL,
    
    engine VARCHAR NOT NULL,  -- http | playwright | provider
    status_code INTEGER,
    
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### `field_maps` Extensions
```sql
ALTER TABLE field_maps ADD COLUMN selector_version VARCHAR NOT NULL DEFAULT '1';
ALTER TABLE field_maps ADD COLUMN selector_history JSONB NOT NULL DEFAULT '[]';
ALTER TABLE field_maps ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
```

---

## API Endpoints

### `GET /interventions/`
List pending intervention tasks.

**Query Parameters:**
- `status` - Filter by status (pending, in_progress, completed, expired)
- `type` - Filter by type (selector_fix, field_confirm, etc.)
- `priority` - Filter by priority (low, normal, high, critical)
- `job_id` - Filter by job ID
- `limit` - Max results (default: 50, max: 100)

**Response:**
```json
[
  {
    "id": "abc123",
    "job_id": "job456",
    "run_id": "run789",
    "type": "field_confirm",
    "status": "pending",
    "trigger_reason": "low_confidence",
    "payload": {
      "field_name": "email",
      "raw_value": "not-an-email",
      "parsed_value": null,
      "confidence": 0.1,
      "reasons": ["normalized_case"],
      "errors": ["invalid_email_format"],
      "field_type": "email"
    },
    "priority": "high",
    "created_at": "2026-01-11T22:00:00Z"
  }
]
```

### `GET /interventions/{task_id}`
Get specific intervention task details.

### `POST /interventions/{task_id}/resolve`
Resolve an intervention task.

**Request:**
```json
{
  "resolution": {
    "action": "edit",
    "value": "john@company.com"
  },
  "resolved_by": "user_123"
}
```

**Response:**
```json
{
  "task": {...},
  "applied": true,
  "resume": {
    "resumed": true,
    "new_run_id": "run999",
    "original_run_id": "run789"
  }
}
```

### `POST /interventions/{task_id}/cancel`
Cancel a pending intervention.

---

## Selector Versioning

### How It Works
1. Human fixes selector via HITL
2. System creates new version:
   ```json
   {
     "selector_version": "2",
     "selector_history": [
       {
         "version": "1",
         "selector": ".old-selector",
         "updated_at": "2026-01-11T21:00:00Z",
         "updated_by": "system"
       }
     ]
   }
   ```
3. Future runs use version "2"
4. Historical data remains unchanged

### API
```python
from app.services.selector_versioning import update_selector, get_selector_history, rollback_selector

# Update selector
field_map = update_selector(
    db=db,
    field_map_id="fm123",
    new_selector=".new-product-title",
    updated_by="user_456"
)

# Get history
history = get_selector_history(db=db, field_map_id="fm123")

# Rollback
field_map = rollback_selector(db=db, field_map_id="fm123", target_version="1")
```

---

## Page Snapshot Capture

### Purpose
Capture page state at extraction time for **replay-first UI**.

**NOT** live browser - recorded state.

### When Captured
- On extraction failure (for selector_fix interventions)
- On low-confidence fields (for field_confirm interventions)
- Optionally on all runs (for audit trail)

### API
```python
from app.services.snapshot_capture import capture_snapshot, get_latest_snapshot

# Capture
snapshot = capture_snapshot(
    db=db,
    job_id="job123",
    run_id="run456",
    url="https://example.com",
    html_content=html,
    engine="http",
    status_code=200
)

# Retrieve
snapshot = get_latest_snapshot(db=db, job_id="job123", run_id="run456")
truncated_html = snapshot.truncate_html(max_bytes=100000)
```

---

## Auto-Resume Pipeline

### Flow
1. Intervention resolved
2. System applies resolution (creates rule, not patch)
3. New run created with updated config
4. Celery task enqueued: `runs.execute`
5. Run executes with fix applied

### Code
```python
# In resolve_intervention endpoint
if task.type in ["selector_fix", "login_refresh"]:
    run = db.query(Run).filter(Run.id == task.run_id).one_or_none()
    if run and run.status == "failed":
        # Create new run
        new_run = create_run(db, str(job.id))
        db.commit()
        
        # Enqueue
        celery_app.send_task("runs.execute", args=[str(new_run.id)])
```

---

## Integration Points

### Worker Integration
```python
# In execute_run task

# 1. After SmartFields processing
for field_result in smartfields_meta.values():
    intervention_spec = InterventionEngine.should_intervene_field_confidence(...)
    if intervention_spec:
        InterventionEngine.create_intervention(...)

# 2. After auth failure
auth_spec = InterventionEngine.should_intervene_auth_expired(...)
if auth_spec:
    InterventionEngine.create_intervention(...)

# 3. After hard block
hard_block_spec = InterventionEngine.should_intervene_hard_block(...)
if hard_block_spec:
    InterventionEngine.create_intervention(...)
```

### Intervention Engine
```python
from app.services.intervention_engine import InterventionEngine

# Check triggers
spec = InterventionEngine.should_intervene_field_confidence(
    field_name="email",
    field_result={"confidence": 0.5, "value": null, "errors": [...]},
    is_required=True
)

# Create intervention
task = InterventionEngine.create_intervention(
    db=db,
    job_id="job123",
    run_id="run456",
    intervention_spec=spec
)

# Apply resolution
applied = InterventionEngine.apply_resolution(
    db=db,
    task=task,
    target_job=job
)
```

---

## Why This Is Better Than Octoparse

| Feature | Octoparse | Our System |
|---------|-----------|------------|
| **Trigger** | Manual watching | Evidence-based (confidence < 0.75, drift, etc.) |
| **Interface** | Live browser (fragile) | Recorded state (reproducible) |
| **Learning** | None | Rules generated, future runs improved |
| **Audit Trail** | Minimal | Full history (task, resolution, version) |
| **Determinism** | Random fixes | Versioned selectors, structured resolutions |
| **Scalability** | Requires constant human attention | Triggers only when necessary |
| **Resume** | Manual restart | Automatic with updated config |

---

## Example Flow: Selector Drift

### 1. Run Fails (Selector Drift Detected)
```
Worker detects:
- Old selector: `.product-title`
- Extraction: empty
- Page structure changed
```

### 2. Intervention Created
```json
{
  "type": "selector_fix",
  "trigger_reason": "selector_drift",
  "priority": "high",
  "payload": {
    "field_name": "title",
    "old_selector": ".product-title",
    "page_snapshot": "...",
    "extraction_result": null
  }
}
```

### 3. Human Views Task
```
GET /interventions/
→ Returns intervention with page snapshot
```

### 4. Human Clicks Element
```
UI shows recorded page
Human clicks ".new-product-title"
System generates new selector
```

### 5. Human Resolves
```
POST /interventions/{id}/resolve
{
  "resolution": {
    "new_selector": ".new-product-title"
  }
}
```

### 6. System Applies
```
- Updates FieldMap.selector_spec = ".new-product-title"
- Increments FieldMap.selector_version = "2"
- Adds history entry to FieldMap.selector_history
- Creates new run with updated selector
- Enqueues run: celery_app.send_task("runs.execute")
```

### 7. Auto-Resume
```
New run executes with:
- selector_version = "2"
- selector = ".new-product-title"
→ Extraction succeeds
```

---

## Testing HITL

### 1. Create Low-Confidence Field
```bash
# Create job with required email field
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com",
    "fields": ["email"]
  }'

# Set field map with strict validation
curl -X PUT http://localhost:8000/jobs/{job_id}/field-maps \
  -H "Content-Type: application/json" \
  -d '{
    "mappings": [{
      "field_name": "email",
      "selector_spec": {"css": ".contact-email"},
      "field_type": "email",
      "validation_rules": {"required": true}
    }]
  }'

# Run job (will extract invalid email)
curl -X POST http://localhost:8000/jobs/{job_id}/runs

# Check for intervention
curl http://localhost:8000/interventions/
```

### 2. Resolve Intervention
```bash
curl -X POST http://localhost:8000/interventions/{task_id}/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "resolution": {
      "action": "edit",
      "value": "john@company.com"
    },
    "resolved_by": "test_user"
  }'
```

### 3. Verify Auto-Resume
```bash
# Check that new run was created
curl http://localhost:8000/jobs/{job_id}/runs

# New run should have corrected value
curl http://localhost:8000/jobs/{job_id}/runs/{new_run_id}/records
```

---

## Configuration

### Confidence Threshold
```python
# app/services/intervention_engine.py
class InterventionEngine:
    LOW_CONFIDENCE_THRESHOLD = 0.75  # Adjust as needed
```

### Max Auto-Retries
```python
class InterventionEngine:
    MAX_AUTO_RETRIES = 3  # Before escalating to manual
```

---

## Future Enhancements

### 1. Batch Resolution
- Resolve multiple similar interventions at once
- Apply same fix to all jobs with similar selector drift

### 2. ML-Assisted Suggestions
- Suggest selector fixes based on historical resolutions
- Predict likely field corrections

### 3. Intervention Analytics
- Track intervention frequency per job
- Identify jobs that need most human attention
- Suggest job improvements

### 4. Collaborative Resolution
- Multiple users can claim/resolve tasks
- Real-time collaboration on complex fixes

---

## Summary

HITL is now **event-driven, replay-first, and deterministic**:

✅ **Triggered by system** (not manual)  
✅ **Evidence-based** (confidence, drift, auth, blocks)  
✅ **Replay-first** (recorded state, not live browser)  
✅ **Generates rules** (selector versions, normalization rules)  
✅ **Never mutates history** (all changes are versioned)  
✅ **Auto-resumes** (new run with updated config)  
✅ **Fully auditable** (intervention_tasks, selector_history, page_snapshots)  

**This is enterprise-grade HITL.**
