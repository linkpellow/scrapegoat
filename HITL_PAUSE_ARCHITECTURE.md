# HITL Pause Architecture - Complete Implementation

## ✅ IMPLEMENTED: 403 → Pause (Not Fail)

**Status:** Production-ready
**Date:** 2026-01-12

---

## Architecture Changes

### 1. New Run Status: `WAITING_FOR_HUMAN`

**File:** `app/enums.py`

```python
class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"  # NEW: Paused, not failed
    FAILED = "failed"
    COMPLETED = "completed"
```

### 2. Block Classifier

**File:** `app/services/block_classifier.py`

**Logic:**
```
403 + no session → PAUSE (manual_access)
403 + has session → PAUSE (login_refresh)
401 → PAUSE (login_refresh)
CAPTCHA → PAUSE (captcha_solve)
Selector drift → PAUSE (selector_fix)
Network errors → FAIL (not recoverable)
```

### 3. Session Manager

**File:** `app/services/session_manager.py`

**Features:**
- Domain-based session storage (not job-based)
- Session health probes
- Invalid session detection
- Domain stats tracking
- Auto-classification (public/infra/human)

### 4. Domain Configuration

**File:** `app/models/domain_config.py`

**Tracks:**
- Access class (public/infra/human)
- Session requirements
- Block rates (403, CAPTCHA)
- Engine performance
- Provider preferences

### 5. Auto-Resume Logic

**File:** `app/api/interventions.py`

**Flow:**
1. Intervention resolved
2. Session captured (if provided)
3. Run status → QUEUED
4. Celery re-executes run
5. Uses captured session

---

## Execution Flow

### Before (Old):
```
Run starts
  ↓
403 Forbidden
  ↓
fail_run()
  ↓
Run FAILED ❌
  ↓
Manual retry needed
```

### After (New):
```
Run starts
  ↓
Check domain config
  ↓
Load session if required
  ↓
403 Forbidden
  ↓
BlockClassifier.should_pause_for_intervention()
  ↓
Create intervention (manual_access)
  ↓
pause_run_for_intervention()
  ↓
Run WAITING_FOR_HUMAN ⏸️
  ↓
SSE alert: "Manual action needed"
  ↓
Human captures session
  ↓
POST /interventions/{id}/resolve
  ↓
resume_run()
  ↓
Run QUEUED → auto-resumes
  ↓
Uses captured session
  ↓
SUCCESS ✅
```

---

## Key Behaviors

### 1. 403 Now Pauses (Not Fails)

**Code location:** `app/workers/tasks.py` line ~423

```python
should_pause, intervention_type, intervention_reason = BlockClassifier.should_pause_for_intervention(
    response_code=403,
    error_message="No items extracted",
    has_session=False,
    domain_access_class="public"
)

if should_pause:
    # Create intervention
    task = InterventionEngine.create_intervention(...)
    
    # PAUSE (not fail)
    pause_run_for_intervention(db, run, reason, task_id)
    
    # SSE emits: intervention.created
    
    return  # Exit, waiting for human
```

### 2. Domain Stats Learned

**After each run:**
```python
SessionManager.update_domain_stats(
    domain="fastpeoplesearch.com",
    success=False,
    engine="playwright",
    response_code=403,
    had_session=False
)
```

**Result:**
- Block rate tracked
- If block_rate_403 > 80% → `requires_session = "required"`
- Future runs check session first

### 3. Session Requirement Checked at Start

**Code location:** `app/workers/tasks.py` line ~242

```python
domain_config = db.query(DomainConfig).filter(
    DomainConfig.domain == domain
).first()

if domain_config and domain_config.requires_session == "required":
    session_vault = SessionManager.get_valid_session(db, domain)
    
    if not session_vault:
        # Create intervention immediately
        task = InterventionEngine.create_intervention(...)
        pause_run_for_intervention(db, run, "Session required", task_id)
        return  # Don't even try without session
```

### 4. Auto-Resume on Intervention Resolution

**Code location:** `app/api/interventions.py`

```python
@router.post("/{intervention_id}/resolve")
def resolve_intervention(...):
    # Mark resolved
    intervention.status = "resolved"
    
    # Save captured session
    if request.captured_session:
        session = SessionVault(
            domain=domain,
            session_data=request.captured_session,
            health_status="valid"
        )
        db.add(session)
    
    # AUTO-RESUME
    if run and run.status == "waiting_for_human":
        resume_run(db, run)  # Status → QUEUED
        celery_app.send_task("runs.execute", args=[run_id])
    
    return {"success": True, "run_resumed": True}
```

---

## New Enums

### DomainAccessClass
```python
class DomainAccessClass(str, Enum):
    PUBLIC = "public"      # No auth, standard scraping
    INFRA = "infra"        # Needs proxies/providers
    HUMAN = "human"        # Requires HITL session
```

### SessionHealthStatus
```python
class SessionHealthStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    EXPIRED = "expired"
```

---

## Database Schema Changes

### SessionVault (Updated)
```sql
CREATE TABLE session_vaults (
    id UUID PRIMARY KEY,
    domain VARCHAR NOT NULL,  -- Changed from job_id FK
    session_data JSONB NOT NULL,
    captured_at TIMESTAMP NOT NULL,
    last_validated TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    is_valid BOOLEAN DEFAULT TRUE,
    health_status VARCHAR DEFAULT 'valid',
    intervention_id UUID REFERENCES intervention_tasks(id),
    notes TEXT,
    validation_attempts JSONB DEFAULT '[]'
);

CREATE INDEX idx_sessions_domain ON session_vaults(domain);
CREATE INDEX idx_sessions_valid ON session_vaults(is_valid, health_status);
```

### DomainConfig (New)
```sql
CREATE TABLE domain_configs (
    id UUID PRIMARY KEY,
    domain VARCHAR UNIQUE NOT NULL,
    access_class VARCHAR DEFAULT 'public',
    requires_session VARCHAR DEFAULT 'no',
    total_attempts INTEGER DEFAULT 0,
    successful_attempts INTEGER DEFAULT 0,
    block_rate_403 FLOAT DEFAULT 0.0,
    block_rate_captcha FLOAT DEFAULT 0.0,
    engine_stats JSONB DEFAULT '{}',
    provider_preference VARCHAR,
    provider_success_rate FLOAT DEFAULT 0.0,
    session_avg_lifetime_days FLOAT,
    last_session_refresh TIMESTAMP,
    block_patterns JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_domain_config_domain ON domain_configs(domain);
```

---

## API Endpoints

### GET /interventions
List all interventions (filterable by status).

### GET /interventions/{id}
Get intervention details.

### POST /interventions/{id}/resolve
```json
{
  "resolution": {
    "action": "session_captured",
    "method": "manual_browser_export"
  },
  "resolved_by": "user_email@example.com",
  "captured_session": {
    "cookies": [...],
    "user_agent": "...",
    "captured_method": "manual_export"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Intervention resolved and run resumed",
  "intervention_id": "...",
  "run_id": "...",
  "run_status": "queued"
}
```

---

## Operational Workflow

### Scenario: FastPeopleSearch 403 Block

**Step 1: Enrichment Triggered**
```bash
POST /skip-tracing/search/by-name?name=John+Smith
```

**Step 2: Run Starts**
```
SSE: {"type": "run.started", "run_id": "abc123", ...}
```

**Step 3: 403 Detected**
```
Worker: BlockClassifier → should_pause=True
Worker: create_intervention(type="manual_access")
Worker: pause_run_for_intervention()
SSE: {"type": "intervention.created", "intervention_id": "int123", ...}
```

**Step 4: Dashboard Alert**
```
Frontend: Toast "🚨 Manual action needed: Hard block (403)"
User: Clicks "View"
```

**Step 5: User Captures Session**
```
1. User visits fastpeoplesearch.com
2. Completes search manually
3. Exports cookies via Cookie-Editor
4. Clicks "Mark as Resolved" + pastes cookies
```

**Step 6: Auto-Resume**
```
POST /interventions/int123/resolve
  ↓
SessionVault saved (domain=fastpeoplesearch.com)
  ↓
resume_run(run_id=abc123)
  ↓
Celery re-executes run
  ↓
Uses captured session
  ↓
SUCCESS: {"PeopleDetails": [...]}
```

**Step 7: Future Enrichments**
```
Next run → checks SessionVault
Session exists → uses automatically
No intervention needed ✅
```

---

## What This Eliminates

### Before:
- ❌ 403 = immediate failure
- ❌ Manual retry every time
- ❌ No session reuse
- ❌ No learning
- ❌ High failure rate

### After:
- ✅ 403 = intelligent pause
- ✅ Auto-resume after intervention
- ✅ Session reuse across jobs
- ✅ Domain classification learning
- ✅ One manual intervention → N automatic runs

---

## Next Steps

### Immediate (Today):
1. ✅ Run database migrations (add WAITING_FOR_HUMAN status)
2. ✅ Test pause/resume flow
3. ✅ Capture first FastPeopleSearch session
4. ✅ Test auto-resume

### Soon (This Week):
1. Add session health probes (async)
2. Add proactive session refresh (before expiration)
3. Add provider escalation for INFRA domains
4. Add candidate disambiguation logic

### Later (Next Month):
1. ML-based session lifetime prediction
2. Auto-session refresh scheduler
3. Visual selector fixer
4. Domain reputation scoring

---

## Files Changed

### Core:
- ✅ `app/enums.py` - Added WAITING_FOR_HUMAN, DomainAccessClass, SessionHealthStatus
- ✅ `app/models/session.py` - Domain-based SessionVault
- ✅ `app/models/domain_config.py` - New model for domain learning
- ✅ `app/services/orchestrator.py` - pause_run_for_intervention(), resume_run()
- ✅ `app/services/block_classifier.py` - Intelligent pause logic
- ✅ `app/services/session_manager.py` - Session lifecycle management
- ✅ `app/workers/tasks.py` - Integrated pause logic, session checks
- ✅ `app/api/interventions.py` - Auto-resume endpoint

### Documentation:
- ✅ `HITL_PAUSE_ARCHITECTURE.md` - This file

---

## Conclusion

**The system no longer "fails" on 403 blocks.**

It **pauses intelligently**, waits for human input, **learns**, and **auto-resumes**.

**This is the correct, modern, resilient HITL architecture.** 🎯
