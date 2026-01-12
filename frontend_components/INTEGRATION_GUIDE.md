# HITL Dashboard - Integration Guide

## Quick Start (5 minutes)

### Step 1: Copy Component
```bash
# Copy HITLDashboard.tsx to your brainscraper.io project
cp frontend_components/HITLDashboard.tsx your-brainscraper-app/components/
```

### Step 2: Add Environment Variable
```bash
# In your brainscraper.io .env.local:
NEXT_PUBLIC_SCRAPER_API_URL=http://localhost:8000
# or your deployed scraper URL
```

### Step 3: Add to Admin Panel
```typescript
// pages/admin/hitl.tsx
import { HITLDashboard } from '@/components/HITLDashboard';

export default function HITLPage() {
  return (
    <div>
      <HITLDashboard />
    </div>
  );
}
```

### Step 4: Install Toast Library (if needed)
```bash
npm install sonner
# or use your existing toast library (react-hot-toast, etc.)
```

---

## What You Get

### Real-Time Monitoring
- See active enrichment runs live
- Get notified when manual action needed
- Track success/failure rates

### Intervention Management
- Toast notifications when HITL needed
- One-click to view intervention details
- Manual resolution workflow
- Auto-resume after resolution

### Zero Polling
- SSE (Server-Sent Events) for real-time updates
- No API polling = less load
- Instant notifications

---

## Testing

### 1. Start Scraper Backend
```bash
cd /Users/linkpellow/SCRAPER
./start_backend.sh
```

### 2. Start brainscraper.io
```bash
cd your-brainscraper-app
npm run dev
```

### 3. Trigger Enrichment
```bash
# In another terminal
curl -X POST "http://localhost:8000/skip-tracing/search/by-name?name=John+Smith"
```

### 4. Watch Dashboard
Open `http://localhost:3000/admin/hitl` and you should see:
- Run appears in "Active Runs"
- If blocked (403), intervention alert pops up
- Click notification to view details
- Mark as resolved after manual completion

---

## Customization

### Toast Library
If you use a different toast library, replace the toast calls:

```typescript
// Replace:
import { toast } from 'sonner';

// With your library:
import toast from 'react-hot-toast';
// or
import { toast } from 'react-toastify';
```

### Styling
The component uses Tailwind CSS. Adjust classes to match your design system.

### API URL
Set via environment variable:
```bash
# Development
NEXT_PUBLIC_SCRAPER_API_URL=http://localhost:8000

# Production
NEXT_PUBLIC_SCRAPER_API_URL=https://scraper.yourdomain.com
```

---

## Event Types

The dashboard listens for these SSE events:

| Event | Description | Action |
|-------|-------------|--------|
| `run.started` | Enrichment started | Add to active runs |
| `intervention.created` | Manual action needed | Show toast alert |
| `intervention.resolved` | Intervention completed | Remove from list |
| `run.completed` | Enrichment succeeded | Remove from active runs |
| `run.failed` | Enrichment failed | Remove from active runs |

---

## Production Deployment

### CORS
Your scraper backend needs to allow your frontend domain:

```python
# In scraper's app/main.py (already configured):
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://brainscraper.io",
        "https://www.brainscraper.io",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### SSL/TLS
For production, use HTTPS for both frontend and SSE:
```bash
NEXT_PUBLIC_SCRAPER_API_URL=https://scraper.brainscraper.io
```

### Monitoring
Add error tracking:
```typescript
eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Send to Sentry, LogRocket, etc.
};
```

---

## Troubleshooting

### "Failed to connect to SSE"
- Check `NEXT_PUBLIC_SCRAPER_API_URL` is correct
- Verify scraper backend is running
- Check CORS configuration
- Test SSE endpoint directly: `curl -N http://localhost:8000/events/runs/events`

### "No events received"
- Ensure Celery worker is running
- Check Redis is running
- Test by triggering enrichment manually
- Check browser console for errors

### "Intervention not loading"
- Check `/interventions/{id}` endpoint works
- Verify intervention was created in database
- Check browser network tab for 404/500 errors

---

## Next Steps

### Phase 3 Features (Later)
Once basic dashboard is working, you can add:

1. **Session Capture UI**
   - Embedded browser window
   - One-click cookie export
   - Auto-apply to SessionVault

2. **Selector Mapper**
   - Click-to-map broken selectors
   - Visual selector diffing
   - One-click fix + versioning

3. **Analytics**
   - Success rate charts
   - Intervention frequency
   - Cost tracking
   - Engine performance

But for now, the basic dashboard gives you:
- ✅ Real-time visibility
- ✅ Instant alerts
- ✅ Manual intervention workflow
- ✅ Production-ready monitoring

**This is enough to make HITL operational.**
