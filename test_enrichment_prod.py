#!/usr/bin/env python3
"""
Test enrichment in production with DataDome-aware Playwright + JSON-LD
"""
import httpx
import time
import json

API_URL = "https://scrapegoat-production.up.railway.app"

print("🎯 TESTING: Link Pellow, Dowagiac, MI Enrichment")
print(f"API: {API_URL}")
print("=" * 80)

# Test enrichment
test_params = {
    "name": "Link Pellow",
    "city": "Dowagiac",
    "state": "MI"
}

print(f"\n📤 Sending enrichment request...")
print(f"Parameters: {json.dumps(test_params, indent=2)}")

try:
    start_time = time.time()
    
    response = httpx.post(
        f"{API_URL}/skip-tracing/search/by-name",
        params=test_params,
        timeout=120.0  # 2 minute timeout
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ Response received ({elapsed:.1f}s)")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        print("\n" + "=" * 80)
        print("📋 ENRICHMENT RESULT:")
        print("=" * 80)
        print(json.dumps(data, indent=2))
        
        # Check for records
        records = data.get("records", [])
        if records:
            print(f"\n✅ SUCCESS: Found {len(records)} enriched records!")
            
            for i, record in enumerate(records, 1):
                print(f"\n📇 Record {i}:")
                print(f"  Name: {record.get('name')}")
                print(f"  Phone: {record.get('phone')}")
                print(f"  Address: {record.get('address')}")
                print(f"  City: {record.get('city')}")
                print(f"  State: {record.get('state')}")
                print(f"  Zip: {record.get('zip')}")
                if 'age' in record:
                    print(f"  Age: {record.get('age')}")
                if 'relatives' in record:
                    print(f"  Relatives: {record.get('relatives')}")
        else:
            print(f"\n⚠️  No records found")
            print(f"Site used: {data.get('site')}")
            print(f"Message: {data.get('message')}")
    
    else:
        print(f"\n❌ ERROR Response:")
        print(response.text[:500])

except httpx.TimeoutException as e:
    print(f"\n❌ TIMEOUT: Request took longer than 120s")
    print(f"This suggests worker is still processing or stuck")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
