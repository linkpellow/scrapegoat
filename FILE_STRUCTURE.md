# 📁 Site Testing - File Structure

## Quick Navigation

```
SCRAPER/
│
├── 🚀 START HERE
│   ├── START_HERE.md                    ← Read this first!
│   ├── READY_TO_TEST.md                 ← Quick start guide
│   └── TESTING_QUICK_REFERENCE.md       ← Command cheat sheet
│
├── 🧪 TESTING SCRIPTS
│   ├── ./quick_site_test.sh             ← Test one site (executable)
│   ├── ./run_all_site_tests.sh          ← Test all sites (executable)
│   ├── test_site_comparison.py          ← Full comparison with rankings
│   └── test_url_generation.py           ← Verify URL generation
│
├── ⚙️  CONFIGURATIONS
│   ├── app/people_search_sites.py       ← 6 sites with REAL selectors
│   ├── app/api/skip_tracing.py          ← Test endpoint + SITE_PRIORITY
│   ├── app/services/people_search_adapter.py  ← Smart URL builder
│   └── app/scraping/extraction.py       ← Regex extraction engine
│
├── 📊 DOCUMENTATION
│   ├── IMPLEMENTATION_COMPLETE.md       ← What was delivered
│   ├── SITE_RANKING_ANALYSIS.md         ← Predictions & analysis
│   ├── SITE_TESTING_SUMMARY.md          ← Complete testing guide
│   └── SITE_COMPARISON_GUIDE.md         ← How comparison works
│
└── 🌐 SITE CONFIGS (in people_search_sites.py)
    ├── ThatsThem         → Real selectors from name_results.html
    ├── SearchPeopleFree  → Real selectors from search_link_pellow.html
    ├── ZabaSearch        → Real selectors from link_pellow_info.html
    ├── AnyWho            → Generic selectors (needs tuning)
    ├── FastPeopleSearch  → Existing config
    └── TruePeopleSearch  → Existing config
```

---

## What To Read When

### **Just Starting?**
→ `START_HERE.md`

### **Ready to Test?**
→ `TESTING_QUICK_REFERENCE.md`

### **Need Detailed Instructions?**
→ `SITE_TESTING_SUMMARY.md`

### **Want to Understand Predictions?**
→ `SITE_RANKING_ANALYSIS.md`

### **Troubleshooting?**
→ `SITE_TESTING_SUMMARY.md` → Troubleshooting section

---

## What To Run When

### **First Time Testing:**
```bash
./quick_site_test.sh thatsthem "Link Pellow" "Dowagiac" "MI"
```

### **Testing All Sites:**
```bash
./run_all_site_tests.sh
```

### **Final Rankings:**
```bash
python test_site_comparison.py
```

### **Debugging:**
```bash
# Check URL generation
python test_url_generation.py

# Check logs
tail -f logs/*.log | grep "\[TEST\]"

# Check saved results
cat site_test_thatsthem_*.json | jq '.records[0]'
```

---

## Site Configuration Details

### ThatsThem (app/people_search_sites.py lines ~273-350)
```python
THATS_THEM = {
    "search_by_name": {
        "url_template": "https://thatsthem.com/name/{name}/{city}-{state_upper}",
        "engine_mode": "playwright",  # Bypasses captcha
        "fields": {
            "name": {"css": "div.card div.name a.web"},
            "age": {"css": "div.card div.age", "regex": r"\((\d+)\s+years? old\)"},
            "phone": {"css": "div.phone span.number a.web", "all": True},
            "email": {"css": "div.email span.inbox a.web", "all": True},
            ...
        }
    }
}
```

### SearchPeopleFree (lines ~351-410)
```python
SEARCH_PEOPLE_FREE = {
    "search_by_name": {
        "url_template": "https://www.searchpeoplefree.com/find/{name}/{state}/{city}",
        "crawl_mode": "list",  # Multiple results
        "fields": {
            "name": {"css": "h2.h2 a"},
            "age": {"css": "h3.mb-3 span", "regex": r"(\d+)"},
            "phone": {"css": "a[href*='phone-lookup']", "all": True},
            ...
        }
    }
}
```

### ZabaSearch (lines ~411-470)
```python
ZABA_SEARCH = {
    "search_by_name": {
        "url_template": "https://www.zabasearch.com/people/{name}/{state_full}/{city}/",
        "fields": {
            "name": {"css": "div#container-name h2 a"},
            "age": {"css": "div#container-name + div h3"},
            "phone": {"css": "... Associated Phone Numbers ... li a", "all": True},
            "email": {"css": "... Associated Email Addresses ... li", "all": True},
            ...
        }
    }
}
```

---

## Testing Results Location

All test results saved to:
```
SCRAPER/
├── site_test_thatsthem_20260112_*.json      ← Quick test results
├── site_test_searchpeoplefree_*.json
├── site_test_zabasearch_*.json
├── all_sites_test_20260112_*.txt            ← All sites summary
└── site_comparison_results_20260112_*.json  ← Full comparison
```

---

## Production Update Location

After testing, update this file:
```python
# app/api/skip_tracing.py (line ~41)

SITE_PRIORITY = [
    "thatsthem",         # Update with your winners
    "searchpeoplefree",
    "zabasearch"
]
```

---

## Everything You Need

✅ **Real configurations** (from your HTML files)
✅ **Test scripts** (ready to run)
✅ **Documentation** (complete guides)
✅ **API endpoint** (test mode)
✅ **Smart URL builder** (handles all formats)
✅ **Regex extraction** (advanced parsing)
✅ **Comparison algorithm** (weighted scoring)
✅ **Rankings generator** (automated recommendations)

**Status: 100% READY TO TEST** 🎯

**First command:**
```bash
./quick_site_test.sh thatsthem "Link Pellow" "Dowagiac" "MI"
```

**GO!** 🚀
