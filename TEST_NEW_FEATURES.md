# 🧪 Testing Guide - New Features

**What's New:** All Runs, Data Explorer, Sessions, Settings pages are now fully functional!

---

## 🚀 QUICK START

### 1. Restart Your Servers

The API server should auto-reload, but if not, restart to load new endpoints:

**Terminal 1 - API (if needed):**
```bash
cd /Users/linkpellow/SCRAPER
source venv/bin/activate
make start
```

**Terminal 3 - Web UI:**
The Next.js dev server should hot-reload automatically. If you see any issues, restart:
```bash
cd /Users/linkpellow/SCRAPER
make start-web
```

---

## ✅ FEATURES TO TEST

### 1. All Runs Page (/runs)

**What it does:** Shows run history across ALL jobs

**How to test:**
1. Go to http://localhost:3000/runs
2. You should see all your runs from all jobs
3. Try the filters:
   - Filter by job (dropdown)
   - Filter by status (dropdown)
   - Search by job URL or run ID
4. Click a run to see details
5. View records in the drawer
6. Click "View Job" to go to that job

**What you should see:**
- Stats cards (Total, Completed, Failed, Total Records)
- List of all runs with status indicators
- Ability to filter and search
- Drawer with run details

---

### 2. Data Explorer (/data)

**What it does:** Browse all extracted records and export data

**How to test:**
1. Go to http://localhost:3000/data
2. You should see all records from all jobs
3. Try these features:
   - **Filter by job** (dropdown)
   - **Search** in record data
   - **Select visible fields** (click field names)
   - **Export to JSON** (button in top-right)
   - **Export to CSV** (button in top-right)
   - **Delete a record** (Delete button on row)
4. Check the stats:
   - Total records
   - Last 7 days
   - Records by job

**What you should see:**
- Statistics dashboard
- Data table with your records
- Field selector
- Export buttons
- Search and filter working

**Testing exports:**
1. Click "Export JSON" - should download a `.json` file
2. Click "Export CSV" - should download a `.csv` file
3. Open the files - they should contain your data

---

### 3. Sessions Page (/sessions)

**What it does:** Manage authentication sessions for protected sites

**How to test:**
1. Go to http://localhost:3000/sessions
2. Click "New Session"
3. Select a job (any job works for testing)
4. Paste this test session data:
```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "test123",
      "domain": ".example.com"
    }
  ],
  "storage": {
    "token": "abc123"
  }
}
```
5. Click "Create Session"
6. You should see the session in the list
7. Click "Validate" - should show cookie count
8. Click "Delete" - should remove the session

**What you should see:**
- List of sessions (if any exist)
- Jobs requiring auth
- Create session modal
- Validate and delete actions

---

### 4. Settings Page (/settings)

**What it does:** Configure platform defaults and behavior

**How to test:**
1. Go to http://localhost:3000/settings
2. Change some settings:
   - **Default Strategy:** Change to "Fast Mode"
   - **Max Concurrent Runs:** Change to 5
   - **Default Timeout:** Change to 60
   - **Enable Notifications:** Toggle on
3. You should see "You have unsaved changes" warning
4. Click "Save Changes"
5. Refresh the page
6. Settings should persist
7. Click "Export Settings" - downloads JSON file

**What you should see:**
- All settings loaded from backend
- Unsaved changes warning
- Save button appears when changed
- Settings persist after refresh
- Export downloads a file

---

## 🎯 COMPLETE TESTING FLOW

### End-to-End Test

**Scenario:** Create job → Run it → View everywhere

1. **Create a job:**
   - Go to http://localhost:3000
   - Click "New Job"
   - Enter URL: `https://books.toscrape.com`
   - Add fields: title, price
   - Click "Create Job & Map Fields"

2. **Map fields:**
   - Click elements on the page to map them
   - Save mappings

3. **Run the job:**
   - Go to Overview tab
   - Click "Run Now"

4. **View in All Runs:**
   - Go to http://localhost:3000/runs
   - Your new run should appear
   - Click it to see details

5. **View in Data Explorer:**
   - Go to http://localhost:3000/data
   - Your extracted records should appear
   - Try exporting to CSV
   - Try searching for a value

6. **Configure Settings:**
   - Go to http://localhost:3000/settings
   - Change max concurrent runs
   - Save and verify persistence

---

## 🐛 TROUBLESHOOTING

### "API endpoint not found"
- **Solution:** Restart the API server to load new endpoints
```bash
# In Terminal 1
CTRL+C
make start
```

### "CORS error"
- **Solution:** Already fixed! Just refresh the page

### "No data showing"
- **Solution:** Run a job first to generate data
- Or the filters might be hiding results - reset filters

### "Export not working"
- **Solution:** Check browser console for errors
- Make sure records exist first

### "Settings not saving"
- **Solution:** Check Terminal 1 for API errors
- Settings endpoint should be at `/settings` (root level)

---

## 📊 WHAT TO LOOK FOR

### All Runs Page
✅ Stats cards showing numbers
✅ List of runs with colored status pills
✅ Filter dropdowns working
✅ Search box filtering results
✅ Clicking run opens drawer
✅ Drawer shows records

### Data Explorer
✅ Stats cards with totals
✅ Records by job breakdown
✅ Data table with records
✅ Field selector buttons
✅ Export buttons download files
✅ Delete button removes records
✅ Search filters results

### Sessions
✅ List of existing sessions
✅ "New Session" button opens modal
✅ Can create session with JSON
✅ Validate shows cookie count
✅ Delete removes session
✅ Shows jobs requiring auth

### Settings
✅ All settings loaded
✅ Changing settings shows warning
✅ Save button appears
✅ Settings persist after refresh
✅ Export downloads JSON
✅ System info displayed

---

## 🎉 SUCCESS CRITERIA

**You'll know it's working when:**

1. ✅ All Runs page shows your run history
2. ✅ Data Explorer shows your records
3. ✅ You can export to CSV/JSON
4. ✅ Sessions can be created and managed
5. ✅ Settings save and persist
6. ✅ No console errors
7. ✅ All filters work
8. ✅ All buttons respond

---

## 📝 QUICK TEST CHECKLIST

```
□ API server running (Terminal 1)
□ Celery worker running (Terminal 2)
□ Web UI running (Terminal 3)
□ Home page loads (localhost:3000)
□ All Runs page works (/runs)
□ Data Explorer works (/data)
□ Sessions page works (/sessions)
□ Settings page works (/settings)
□ Can export data to CSV
□ Can export data to JSON
□ Filters work on all pages
□ Can create/delete sessions
□ Settings persist after save
□ No console errors
```

---

## 🚀 NEXT STEPS AFTER TESTING

Once everything works:

1. **Create real jobs** for your use case
2. **Run them regularly** to build up data
3. **Export data** when needed
4. **Set up sessions** for authenticated sites
5. **Configure settings** to match your workflow

---

**Ready to test! Everything is deployed and waiting! 🎉**
