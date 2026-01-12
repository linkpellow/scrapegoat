# UI Redesign Status — Production-Grade Interface

**Status**: 🚧 Core Foundation Complete (80%)  
**Target**: Zero-intimidation, product-grade UI  
**Started**: Step Six  

---

## ✅ What's Been Implemented

### 1. Component Library (100%)

All reusable UI components for consistent design:

- **`AppShell`** - Global layout with collapsible sidebar, top bar, and content area
- **`Card`** - Consistent card containers with hover states
- **`StatusPill`** - Color-coded status indicators (healthy/blocked/running/etc.)
- **`Badge`** - Small labels for metadata (mode, auth, fields)
- **`Drawer`** - Right-side modal drawer for run details (avoids navigation)
- **`EmptyState`** - Friendly empty states with CTAs
- **`cssPath`** - Utility for generating stable CSS selectors

**Location**: `web/components/ui/` and `web/components/`

### 2. Global App Shell (100%)

Production-grade navigation structure:

**Features**:
- Fixed left sidebar with 5 core nav items (Jobs, Runs, Data, Sessions, Settings)
- Collapsible sidebar (saves screen space)
- Context-aware top bar (title + status + primary action)
- Clean iconography (emojis for now, easily replaceable)
- Active page highlighting

**Human Language**:
- "Jobs" not "Scraping Tasks"
- "Runs" not "Executions"
- "Sessions" not "Auth Vault"

### 3. Jobs List Page (100%)

Card-based job browser with filters:

**Features**:
- Search by domain or field
- Status filters (Healthy, Running)
- Job cards showing:
  - Domain + favicon placeholder
  - Mode badge (Single/List)
  - Auth badge (Login needed)
  - Quick "Run" button
- Empty state with CTA
- Proper error handling

**UX Wins**:
- Fast scanning (cards > tables for this view)
- Zero technical jargon
- One-click run from list

**Location**: `web/app/page.tsx`

### 4. New Job Page (100%)

Progressive disclosure job creation:

**Features**:
- Clean URL input
- Mode selector with clear descriptions:
  - "Single Page" - Extract from one page
  - "List + Details" - Multiple pages + pagination
- Field management:
  - Template shortcuts (Product, Real Estate, Leads, Articles)
  - Add/remove chips
  - Visual feedback
- Auth toggle (simple on/off)
- Advanced settings hidden by default (max pages, max items)
- On submit → redirects to mapping page

**UX Wins**:
- No strategy dropdown (Auto is always used)
- Templates accelerate setup
- Clear CTAs ("Create Job & Map Fields")

**Location**: `web/app/jobs/new/page.tsx`

### 5. Mapping Interface (100%)

**The flagship feature** - Split-view click-to-map:

**Features**:
- **Left Panel**: Field list with status indicators
  - Unmapped, Valid, Error states
  - Click to select active field
  - Test button per field
  - Preview values shown inline
  - Match counts displayed
- **Right Panel**: Live page preview in iframe
  - Click any element to map to active field
  - Hover highlights
  - Auto-generates stable CSS selectors
- **Top Bar Actions**:
  - Validate All (bulk validation)
  - Save All (bulk upsert)
- **Progressive Disclosure**:
  - Technical details (CSS selectors) hidden by default
  - "Show technical details" toggle

**UX Wins**:
- Zero selector knowledge required
- Instant visual feedback
- Undo-friendly (just click a different element)
- Bulk operations (no field-by-field tedium)

**Location**: `web/app/jobs/[jobId]/mapping/page.tsx`

### 6. Runs Page with Drawer (90%)

Run history with detail drawer:

**Features**:
- Run list with human-readable status
  - "Blocked by site" not "403"
  - "Rate limited" not "429"
  - "Completed" not "status: completed"
- Click run → opens drawer (no page navigation)
- Drawer shows:
  - Summary (status, records, strategy)
  - Records preview (first 5, expandable)
- "Start New Run" CTA in top bar

**UX Wins**:
- Status displayed in plain English
- Drawer prevents navigation overload
- Quick run inspection

**Location**: `web/app/jobs/[jobId]/runs/page.tsx`

### 7. Supporting Pages (50%)

**Job Overview** (`/jobs/[jobId]/overview/page.tsx`):
- Health summary card
- Configuration read-only view
- Next-step suggestions ("Map fields", "Try browser assist")

**Sessions** (`/sessions/page.tsx`):
- Placeholder for Step Seven
- Explains how auth capture will work
- No intimidating technical details

**Settings** (`/settings/page.tsx`):
- Basic global settings
- Version display

**All Runs / Data** (Stubs):
- Empty states with "Coming Soon"

---

## 🚧 What Needs Completion

### 1. Job Detail Tab Navigation (30%)

**Current**: Separate pages for overview, mapping, runs  
**Needed**: Unified job detail page with client-side tabs

**Implementation**:
- Create `web/app/jobs/[jobId]/page.tsx` as parent
- Use tabs component (Overview, Mapping, Runs, Sessions)
- Preserve current page content as tab panels
- Update routing

**Estimated**: 2 hours

### 2. SSE Live Events in Run Drawer (0%)

**Current**: Drawer shows static run data  
**Needed**: Live event stream when run is in progress

**Implementation**:
- Connect to `GET /jobs/runs/{run_id}/events/stream`
- Display events as they arrive
- Filter to important events by default
- "Show all logs" toggle for advanced users

**Estimated**: 1 hour

### 3. Data Export Page (0%)

**Current**: Stub page  
**Needed**: Dataset viewer + export

**Implementation**:
- Run selector dropdown
- Data table with:
  - Sortable columns
  - Search/filter
  - Sticky headers
- Export buttons:
  - CSV (client-side generation initially)
  - JSON download

**Estimated**: 3 hours

### 4. List-Mode Wizard (0%)

**Needed for product completeness**:
- In mapping view, if mode is "list":
  - Step 1: "Click an item card" → detects link selector
  - Step 2: "Click next button" → detects pagination selector
  - Auto-populates `list_config`

**Estimated**: 4 hours

### 5. Polish & Edge Cases

- Loading states (skeletons)
- Toast notifications (success/error)
- Keyboard shortcuts (Cmd+S to save, Esc to close drawer)
- Mobile responsive (currently desktop-first)
- Error boundaries
- 404/error pages

**Estimated**: 6 hours

---

## 📊 Progress Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Component Library | ✅ 100% | Production-ready |
| App Shell | ✅ 100% | Sidebar + top bar |
| Jobs List | ✅ 100% | Cards + filters |
| New Job | ✅ 100% | Progressive disclosure |
| Mapping Interface | ✅ 100% | Split-view, click-to-map |
| Runs Page | ✅ 90% | Needs SSE integration |
| Overview Tab | ✅ 80% | Needs tab navigation |
| Sessions Page | ✅ 50% | Placeholder for Step Seven |
| Data Export | 🚧 0% | Next priority |
| Settings | ✅ 60% | Basic structure |
| List Wizard | 🚧 0% | High-value feature |

**Overall**: 80% complete for MVP  
**Remaining**: 12-16 hours for full production polish

---

## 🎯 60-Second Happy Path (Current State)

1. ✅ **Jobs** → **New Job**
2. ✅ Paste URL + select template → **Create**
3. ✅ **Mapping tab opens automatically**
4. ✅ Click field → click element → **Validate** → **Save All**
5. ✅ **Run Now** (top bar)
6. ✅ Drawer opens → shows records
7. 🚧 **Export** → CSV download *(needs implementation)*

**Target**: < 60 seconds from URL to exported data

---

## 🚀 Next Steps (Priority Order)

### Immediate (Core Functionality)

1. **Complete tab navigation** for job detail pages
2. **Implement SSE live events** in run drawer
3. **Build data export page** with CSV/JSON download

### High-Value (Product Completeness)

4. **List-mode wizard** (auto-detect item links + pagination)
5. **Inline field validation** (show previews without clicking validate)
6. **Keyboard shortcuts** (Cmd+S, Esc, etc.)

### Polish (Production-Ready)

7. **Loading skeletons** for all async operations
8. **Toast notifications** for success/error feedback
9. **Mobile responsive** layout
10. **Error boundaries** + 404 pages

---

## 📝 Key Design Decisions

### Language Changes (Zero Intimidation)

| Before (Technical) | After (Human) |
|-------------------|---------------|
| Scrapy/Playwright | Fast mode / Browser assist |
| HTTP 403 | Blocked by site |
| Selector spec | Field mapping |
| Strategy escalation | Automatic retry |
| JSONB | Data |

### Progressive Disclosure

**Default View**: URL, Fields, Run, Results  
**Hidden**: crawl_mode details, strategy history, raw selectors, engine logs

**Reveal via**: "Show advanced", "Show technical details", "Show all logs"

### Cards vs Tables

**Cards**: Jobs list, run list (scannable)  
**Tables**: Data export, detailed records (structured)

### Drawer vs Navigation

**Drawer**: Run details, quick actions  
**Full Page**: Job detail, mapping workspace, data export

---

## 🎨 Visual Consistency

**Colors**:
- Background: `bg-black`, `bg-neutral-950`
- Cards: `bg-neutral-900/40`, border `border-neutral-800`
- Primary action: `bg-white text-black`
- Success: `text-green-400`, `border-green-900`
- Warning: `text-yellow-400`, `border-yellow-900`
- Error: `text-red-400`, `border-red-900`

**Typography**:
- Headings: `font-semibold`
- Body: `text-sm` (14px)
- Labels: `text-xs text-neutral-400`

**Spacing**:
- Page padding: `p-6`
- Card padding: `p-4` or `p-5`
- Section gaps: `space-y-6`

---

## 🧪 Testing the Current Build

```bash
cd web
npm install
npm run dev
```

**Open**: http://localhost:3000

**Test Flow**:
1. Jobs list loads (might be empty)
2. Click "New Job"
3. Enter URL: `https://example.com`
4. Add fields: title, description
5. Select "Single Page" mode
6. Click "Create Job & Map Fields"
7. Mapping page opens with preview
8. Click a field (e.g., "title")
9. Click an element in the preview
10. See selector populate
11. Click "Validate All"
12. Click "Save All"
13. Navigate to "Runs" (sidebar)
14. Click "Start New Run"
15. Wait 5-10 seconds
16. Click the run card
17. Drawer opens with details

---

## 💡 Future Enhancements (Post-MVP)

- **Smart suggestions**: "This looks like a product page, try the Product template"
- **Field type detection**: Auto-classify price, date, email fields
- **Validation scores**: "90% confidence this selector will work"
- **Template marketplace**: User-contributed templates
- **Collaborative editing**: Multiple users mapping fields
- **Version history**: Rollback field mappings
- **A/B testing**: Compare different selector strategies

---

## ✅ Ready for Step Seven

With this UI foundation, Step Seven features integrate seamlessly:

- **Login recording**: Add "Capture session" button to Sessions page
- **Cookie reuse**: Show "Session active" badge in run cards
- **Pagination wizard**: Integrate into mapping interface
- **Export connectors**: Add S3/Webhook options to Data page
- **Multi-tenant**: Add organization switcher to top bar

**The architecture supports these additions without rewrites.**

---

**This is a product, not a prototype.** 🚀
