# 🎯 Quick Reference - Site Testing

## One-Command Tests

```bash
# Test ThatsThem (your top choice)
./quick_site_test.sh thatsthem "Link Pellow" "Dowagiac" "MI"

# Test SearchPeopleFree
./quick_site_test.sh searchpeoplefree "Link Pellow" "Dowagiac" "MI"

# Test ZabaSearch
./quick_site_test.sh zabasearch "Link Pellow" "Dowagiac" "MI"

# Test AnyWho
./quick_site_test.sh anywho "Link Pellow" "Dowagiac" "MI"

# Test all sites at once
./run_all_site_tests.sh

# Full comparison with rankings
python test_site_comparison.py
```

---

## Site Summary

| Site | Speed | Data | Selectors | Command |
|------|-------|------|-----------|---------|
| **ThatsThem** ⭐ | 🐢 Slow (12s) | ⭐⭐⭐⭐⭐ Complete | ✅ Real | `./quick_site_test.sh thatsthem` |
| **SearchPeopleFree** | 🚀 Fast (3s) | ⭐⭐⭐⭐ Good | ✅ Real | `./quick_site_test.sh searchpeoplefree` |
| **ZabaSearch** | 🚀 Fast (3s) | ⭐⭐⭐⭐ Good | ✅ Real | `./quick_site_test.sh zabasearch` |
| **AnyWho** | 🚀 Fast (3s) | ⭐⭐⭐ Fair | ⚠️ Generic | `./quick_site_test.sh anywho` |

---

## Expected Data by Site

### ThatsThem (Most Complete)
```json
{
  "name": "Link D. Pellow",
  "age": 29,
  "phone": ["+12694621403", "+12698080381", "+12697825623", "+12698081346"],
  "email": ["linkpellow@hotmail.com", "lpellow@hotmail.com", "julie.pellow@yahoo.com"],
  "address": "7704 Tranquility Loop #306, Wesley Chapel, FL 33545",
  "previous_addresses": ["28805 Fairlane Dr, Dowagiac, MI 49047", ...]
}
```

### SearchPeopleFree (Fast & Good)
```json
{
  "name": "Link Pellow",
  "age": 29,
  "phone": ["+12694621403"],
  "address": "28805 Fairlane Dr, Dowagiac, MI 49047"
}
```

### ZabaSearch (Reliable)
```json
{
  "name": "Link Pellow",
  "age": 28,
  "phone": ["+12697825623", "+12698080381", "+12694621403"],
  "email": ["linkpellow@hotmail.com", ...],
  "address": "28805 Fairlane Dr, Dowagiac, Michigan 49047"
}
```

---

## Predicted Priority Order

**Best Overall:**
```python
SITE_PRIORITY = ["thatsthem", "searchpeoplefree", "zabasearch"]
```

**Speed-Focused:**
```python
SITE_PRIORITY = ["searchpeoplefree", "zabasearch", "fastpeoplesearch"]
```

**Completeness-Focused:**
```python
SITE_PRIORITY = ["thatsthem", "zabasearch", "truepeoplesearch"]
```

---

## Test Now

```bash
./quick_site_test.sh thatsthem "Link Pellow" "Dowagiac" "MI"
```

Expected: ✅ **SUCCESS in 12 seconds with complete data!** 🎉
