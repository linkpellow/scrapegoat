# 🎨 Frontend Completion Roadmap

**Current Status:** Core functionality complete, several features need implementation  
**Priority:** High-impact features first, then nice-to-haves

---

## ✅ COMPLETED PAGES

### 1. Jobs Page (/) ✅
**Status:** Fully functional
- ✅ List all jobs with search/filtering
- ✅ Create new job
- ✅ Quick run button
- ✅ Status indicators
- ✅ Empty states

### 2. Job Creation (/jobs/new) ✅
**Status:** Fully functional
- ✅ URL input
- ✅ Single vs List mode selection
- ✅ Field templates (Product, Real Estate, Leads, Articles)
- ✅ Custom field management
- ✅ Authentication toggle
- ✅ List settings (max pages, max items)

### 3. Field Mapping (/jobs/[jobId]/mapping) ✅
**Status:** Fully functional
- ✅ Visual click-to-map interface
- ✅ Live HTML preview in iframe
- ✅ Hover highlighting
- ✅ Field validation
- ✅ Bulk save/validate
- ✅ ListWizard integration for list mode
- ✅ Technical details toggle

### 4. Job Runs (/jobs/[jobId]/runs) ✅
**Status:** Fully functional
- ✅ List all runs for a job
- ✅ Run status with color coding
- ✅ Create new run
- ✅ View records drawer
- ✅ Stats display (records count, strategy)

---

## ⚠️ INCOMPLETE PAGES

### 5. Job Overview (/jobs/[jobId]/overview) - 60% Complete
**Status:** Partial implementation

**What's Working:**
- ✅ Basic job info display
- ✅ Health summary card
- ✅ Configuration display
- ✅ Status pills

**What's Missing:**
- ❌ "Run Now" button not connected to API
- ❌ "Go to Mapping" button not connected
- ❌ No navigation to other job tabs
- ❌ Real-time status updates
- ❌ Recent runs quick view
- ❌ Action buttons for edit/delete job
- ❌ Health metrics (success rate, avg runtime)

**Required:**
```typescript
// Add to component:
1. Wire up "Run Now" button: onClick={() => createRun(jobId)}
2. Wire up "Go to Mapping" button: router.push(`/jobs/${jobId}/mapping`)
3. Add tab navigation (Overview/Mapping/Runs)
4. Add job edit/delete buttons
5. Show last 3 runs in quick view
6. Calculate and display health metrics
```

---

### 6. Job Detail Page (/jobs/[jobId]/page) - 80% Complete
**Status:** Mostly functional

**What's Working:**
- ✅ Job details display
- ✅ Preview mapper component
- ✅ Runs list
- ✅ SSE live event streaming
- ✅ Records viewer

**What's Missing:**
- ❌ No tab navigation (should have tabs: Overview/Mapping/Runs/Data)
- ❌ Page layout not using AppShell
- ❌ Missing breadcrumb navigation
- ❌ No link to edit job
- ❌ No delete job functionality

**Required:**
```typescript
// Wrap in AppShell with tabs
1. Add tabbed interface
2. Add breadcrumbs
3. Add edit/delete actions in top bar
4. Move this content to /overview tab
```

---

### 7. All Runs Page (/runs) - 0% Complete
**Status:** Placeholder only

**What's Missing:**
- ❌ List runs across ALL jobs (not just one job)
- ❌ Filter by job
- ❌ Filter by status (completed/failed/running)
- ❌ Search by job name/URL
- ❌ Date range filter
- ❌ Click to view run details
- ❌ Export runs data
- ❌ Pagination

**Required API:**
```typescript
// NEW endpoint needed in backend:
GET /runs?limit=50&job_id=optional&status=optional

// Frontend implementation:
1. Create getAllRuns() in lib/api.ts
2. Build runs table with filters
3. Add drawer for run details
4. Add export button (CSV/JSON)
5. Implement pagination
```

---

### 8. Data Page (/data) - 0% Complete
**Status:** Placeholder only

**What's Missing:**
- ❌ Global data explorer (all records across all jobs)
- ❌ Group by job
- ❌ Filter by date range
- ❌ Search records
- ❌ Column selector (choose which fields to show)
- ❌ Export data (CSV, JSON, Excel)
- ❌ Delete records
- ❌ Data statistics (total records, by job, growth chart)
- ❌ Pagination/infinite scroll

**Required API:**
```typescript
// NEW endpoints needed in backend:
GET /records?limit=100&job_id=optional&date_from=optional&date_to=optional
DELETE /records/{record_id}
GET /records/stats  // Aggregate statistics

// Frontend implementation:
1. Create data API functions
2. Build data table component
3. Add export functionality
4. Add filters/search
5. Build stats dashboard
6. Implement pagination
```

---

### 9. Sessions Page (/sessions) - 20% Complete
**Status:** Informational placeholder

**What's Working:**
- ✅ Explanation of how sessions work
- ✅ Empty state

**What's Missing:**
- ❌ List existing sessions
- ❌ Create new session (browser capture flow)
- ❌ Test session validity
- ❌ Delete/update sessions
- ❌ Link sessions to specific jobs
- ❌ Session status indicators (valid/expired)
- ❌ Security warnings
- ❌ View session metadata (created date, last used)

**Required API:**
```typescript
// NEW endpoints needed in backend:
GET /sessions
POST /sessions  // Create via browser capture
DELETE /sessions/{session_id}
POST /sessions/{session_id}/validate

// Frontend implementation:
1. Session list component
2. Browser capture flow (Playwright automation)
3. Session management UI
4. Link to jobs that use each session
5. Security best practices display
```

---

### 10. Settings Page (/settings) - 30% Complete
**Status:** UI shell only, no functionality

**What's Working:**
- ✅ Basic layout
- ✅ UI components (selects, inputs)

**What's Missing:**
- ❌ Settings not saved to backend
- ❌ No global settings API
- ❌ Additional settings:
  - ❌ Notification preferences
  - ❌ API key management
  - ❌ Webhook configuration
  - ❌ Rate limiting settings
  - ❌ Proxy configuration
  - ❌ Timeout settings
  - ❌ Export/import configuration
  - ❌ Theme toggle (dark/light)
  - ❌ Timezone selection

**Required API:**
```typescript
// NEW endpoints needed in backend:
GET /settings
PUT /settings
POST /settings/reset

// Frontend implementation:
1. Create settings state management
2. Add save/reset buttons
3. Add more settings categories
4. Add validation
5. Add confirmation dialogs
6. Show "unsaved changes" warning
```

---

## 📊 PRIORITY ROADMAP

### Phase 1: Critical Fixes (Week 1)
**Goal:** Make existing pages fully functional

1. ✅ **Fix CORS** (DONE)
2. **Job Overview Page**
   - Wire up "Run Now" button
   - Wire up navigation buttons
   - Add tab navigation
3. **Job Detail Page**
   - Add tabbed layout
   - Wrap in AppShell
   - Add breadcrumbs

### Phase 2: Core Features (Week 2)
**Goal:** Complete the data viewing experience

4. **All Runs Page**
   - Backend: Add GET /runs endpoint
   - Frontend: Build runs list with filters
   - Add run details drawer
5. **Data Page - Phase 1**
   - Backend: Add GET /records endpoint
   - Frontend: Basic data table
   - Add simple export (JSON)

### Phase 3: Enhanced Features (Week 3)
**Goal:** Add power-user features

6. **Data Page - Phase 2**
   - Add CSV/Excel export
   - Add filters and search
   - Add statistics dashboard
7. **Sessions Page - Phase 1**
   - Backend: Add session endpoints
   - Frontend: List and delete sessions
   - Add session creation UI

### Phase 4: Polish & Nice-to-Haves (Week 4)
**Goal:** Complete the experience

8. **Sessions Page - Phase 2**
   - Browser capture flow
   - Session validation
   - Job linking
9. **Settings Page**
   - Save settings to backend
   - Add more settings options
   - Add export/import config
10. **Global Enhancements**
    - Add keyboard shortcuts
    - Add bulk actions
    - Add notifications/toasts
    - Add loading skeletons
    - Add error boundaries

---

## 🚀 QUICK WINS (Can do now)

### 1. Job Overview Page Fixes (30 min)
```typescript
// Add to /jobs/[jobId]/overview/page.tsx:

// Wire up Run Now button:
const handleRunNow = async () => {
  await createRun(jobId);
  router.push(`/jobs/${jobId}/runs`);
};

// Wire up Go to Mapping button:
onClick={() => router.push(`/jobs/${jobId}/mapping`)}

// Add to imports:
import { createRun } from "@/lib/api";
import { useRouter } from "next/navigation";
const router = useRouter();
```

### 2. Add Tab Navigation (1 hour)
```typescript
// Create components/ui/Tabs.tsx
// Add to job detail pages
```

### 3. Add Breadcrumbs (30 min)
```typescript
// Add to AppShell or create Breadcrumb component
```

### 4. Add Delete Job (30 min)
```typescript
// Backend: Already has DELETE /jobs/{id} ?
// Frontend: Add deleteJob() to lib/api.ts
// Add delete button with confirmation
```

---

## 📝 NEW BACKEND ENDPOINTS NEEDED

### Required for Frontend Completion:

1. **GET /runs** - List all runs across all jobs
   ```python
   @router.get("/runs", response_model=list[RunRead])
   def list_all_runs(limit: int = 50, job_id: str = None, status: str = None):
       # Return runs with optional filters
   ```

2. **GET /records** - List all records with filters
   ```python
   @router.get("/records", response_model=list[RecordRead])
   def list_all_records(
       limit: int = 100,
       job_id: str = None,
       date_from: str = None,
       date_to: str = None
   ):
       # Return records with filters
   ```

3. **GET /records/stats** - Get aggregate statistics
   ```python
   @router.get("/records/stats")
   def get_records_stats():
       # Return total records, by job, growth data
   ```

4. **GET /sessions** - List sessions
5. **POST /sessions** - Create session via browser capture
6. **DELETE /sessions/{id}** - Delete session
7. **POST /sessions/{id}/validate** - Test session validity

8. **GET /settings** - Get platform settings
9. **PUT /settings** - Update platform settings

10. **DELETE /jobs/{id}** - Delete job (if not implemented)

---

## 🎯 COMPONENTS NEEDED

### Reusable Components:

1. **Tabs Component** - For job detail pages
2. **Breadcrumbs Component** - For navigation
3. **DataTable Component** - For data/runs pages
4. **ExportButton Component** - For CSV/JSON exports
5. **FilterPanel Component** - For data filtering
6. **ConfirmDialog Component** - For destructive actions
7. **Toast/Notification Component** - For user feedback
8. **LoadingSkeleton Component** - For better loading states
9. **ErrorBoundary Component** - For error handling
10. **Pagination Component** - For data tables

---

## 📊 ESTIMATED EFFORT

| Page | Current % | Effort to Complete | Priority |
|------|-----------|-------------------|----------|
| Job Overview | 60% | 4 hours | High |
| Job Detail | 80% | 2 hours | High |
| All Runs | 0% | 8 hours (4h BE + 4h FE) | High |
| Data | 0% | 16 hours (8h BE + 8h FE) | High |
| Sessions | 20% | 12 hours (6h BE + 6h FE) | Medium |
| Settings | 30% | 8 hours (2h BE + 6h FE) | Low |

**Total Estimated Effort:** ~50 hours

---

## ✨ BONUS FEATURES (After Core Completion)

1. **Real-time Updates** - WebSocket for live job/run updates
2. **Scheduling UI** - Cron expression builder for job frequency
3. **Retry Configuration** - UI for retry settings
4. **Rate Limiting UI** - Configure rate limits per job
5. **Webhook Manager** - Set up webhooks for job events
6. **API Key Manager** - Generate API keys for external access
7. **Team Collaboration** - Multi-user support
8. **Audit Log** - Track all user actions
9. **Data Visualization** - Charts for trends
10. **Mobile Responsive** - Optimize for mobile devices

---

**Current Priority:** Fix Job Overview and Job Detail pages, then build All Runs and Data pages.

**Next Review:** After Phase 1 completion
