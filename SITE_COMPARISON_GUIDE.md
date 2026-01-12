# People Search Site Comparison Guide

## Overview

This guide helps you test and compare different people search websites to determine which works best for your skip tracing needs.

## Sites Configured

1. **ThatsThem** - https://thatsthem.com/
2. **AnyWho** - https://www.anywho.com/
3. **SearchPeopleFree** - https://www.searchpeoplefree.com/
4. **ZabaSearch** - https://www.zabasearch.com/
5. **FastPeopleSearch** (existing) - https://www.fastpeoplesearch.com/
6. **TruePeopleSearch** (existing) - https://www.truepeoplesearch.com/

## Quick Test (Single Site)

Test a single site directly:

```bash
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=thatsthem&name=Link+Pellow&city=Dowagiac&state=MI" | jq
```

### Test All Sites

```bash
# Test ThatsThem
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=thatsthem&name=Link+Pellow&city=Dowagiac&state=MI" | jq '.success, .records_count'

# Test AnyWho
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=anywho&name=Link+Pellow&city=Dowagiac&state=MI" | jq '.success, .records_count'

# Test SearchPeopleFree
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=searchpeoplefree&name=Link+Pellow&city=Dowagiac&state=MI" | jq '.success, .records_count'

# Test ZabaSearch
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=zabasearch&name=Link+Pellow&city=Dowagiac&state=MI" | jq '.success, .records_count'
```

## Comprehensive Comparison Test

Run the automated comparison test:

```bash
python test_site_comparison.py
```

This will:
- Test all sites with the same queries
- Track success rate, completeness, accuracy, and speed
- Generate a ranked report
- Save detailed results to JSON

## What the Test Measures

| Metric | Weight | Description |
|--------|--------|-------------|
| **Success Rate** | 35% | % of searches that return results |
| **Data Completeness** | 30% | How many fields are populated (phone, age, address, etc.) |
| **Data Accuracy** | 25% | Are the results correct? (verified against expected values) |
| **Response Time** | 10% | How fast does the site respond? |

## Understanding the Results

### Example Output

```
🏆 RANKINGS:

1. THATSTHEM - Score: 87.5/100
   Success Rate: 100%
   Avg Completeness: 85%
   Avg Accuracy: 95%
   Avg Response Time: 12.3s

2. ANYWHO - Score: 82.3/100
   Success Rate: 90%
   Avg Completeness: 80%
   Avg Accuracy: 90%
   Avg Response Time: 8.5s
   
...
```

### Recommendation Priority

Based on test results, the script will suggest a priority order for your `SITE_PRIORITY` in `app/api/skip_tracing.py`:

```python
SITE_PRIORITY = ["thatsthem", "anywho", "searchpeoplefree"]  # Example
```

## Manual Testing & Debugging

### 1. Check if Site is Working

```bash
# See what URL is being generated
python -c "from app.services.people_search_adapter import PeopleSearchAdapter; \
           print(PeopleSearchAdapter._build_url('https://thatsthem.com/name/{name}/{city}-{state}', \
           {'name': 'Link Pellow', 'city': 'Dowagiac', 'state': 'MI'}))"
```

### 2. Check Scraper Job

```bash
# Test job creation
curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=thatsthem&name=Link+Pellow&city=Dowagiac&state=MI" \
  -H "Content-Type: application/json" | jq
```

### 3. Check Logs

```bash
# Watch backend logs for errors
tail -f logs/*.log | grep "\[TEST\]"
```

## Common Issues & Solutions

### Issue: Captcha Challenges

**Symptoms:** Site returns 0 results or error messages about verification

**Solutions:**
1. Configure site to use `"engine_mode": "playwright"` (already done for ThatsThem)
2. Add delays: `"wait_time": 3000` in site config
3. Use residential proxies if needed

### Issue: Wrong CSS Selectors

**Symptoms:** Job succeeds but extracts 0 fields or wrong data

**Solutions:**
1. Visit the site manually and inspect HTML
2. Update CSS selectors in `app/people_search_sites.py`
3. Test with curl to verify HTML structure:
   ```bash
   curl -s "https://thatsthem.com/name/Link-Pellow/Dowagiac-MI" | grep "class=\"name\""
   ```

### Issue: Site Blocks Requests

**Symptoms:** HTTP 429, 403, or connection timeouts

**Solutions:**
1. Switch to Playwright: `"engine_mode": "playwright"`
2. Add rate limiting delays
3. Rotate user agents
4. Use proxies

## Updating Site Configurations

Sites may change their HTML structure. To update:

1. **Inspect the Live Site:**
   ```bash
   # Fetch HTML
   curl -s "https://thatsthem.com/name/Link-Pellow/Dowagiac-MI" > /tmp/thatsthem.html
   
   # Search for name elements
   grep -i "class.*name" /tmp/thatsthem.html
   ```

2. **Update Selectors:**
   Edit `app/people_search_sites.py`:
   ```python
   "name": {
       "css": "div.new-name-class",  # Update this
       "field_type": "person_name"
   }
   ```

3. **Test the Changes:**
   ```bash
   curl -X POST "http://localhost:8000/skip-tracing/test/search-specific-site?site_name=thatsthem&name=Link+Pellow&city=Dowagiac&state=MI" | jq '.records[0].name'
   ```

## Production Deployment

Once you've identified the best sites:

1. **Update Priority List:**
   Edit `app/api/skip_tracing.py`:
   ```python
   SITE_PRIORITY = ["thatsthem", "anywho", "fastpeoplesearch"]
   ```

2. **Remove Underperforming Sites:**
   Remove sites with <50% success rate from the priority list

3. **Monitor Performance:**
   Track success rates in production and adjust priority accordingly

4. **Set Up Alerts:**
   Monitor for sudden drops in success rate (indicates site changes)

## Next Steps

1. ✅ Sites configured: ThatsThem, AnyWho, SearchPeopleFree, ZabaSearch
2. ✅ Test endpoint added
3. ✅ Comparison script ready
4. ⏳ **You need to:** 
   - Start backend server
   - Start Celery worker  
   - Run `python test_site_comparison.py`
   - Review rankings
   - Update `SITE_PRIORITY` with winners

## Support

If you encounter issues:
1. Check logs: `tail -f logs/*.log`
2. Verify services are running: backend + Celery + Redis + Postgres
3. Test with curl first before using Python script
4. Examine HTML structure if selectors aren't working
