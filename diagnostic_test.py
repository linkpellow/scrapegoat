#!/usr/bin/env python3
"""
Diagnostic test to capture full HTML response, headers, and metadata
for Link Pellow, Dowagiac, MI enrichment
"""
import httpx
import json
from datetime import datetime

# Test ScrapingBee directly
scrapingbee_api_key = "LKC89BNO7ZBOVKLFIAKYK4YE57QSE86O7N2XWOACU2W6ZW2O2Y1M7U326H4YX04438NN9W2WC5R8AI69"
target_url = "https://www.fastpeoplesearch.com/name/link-pellow_dowagiac-mi"

print("🎯 DIAGNOSTIC TEST: Link Pellow, Dowagiac, MI")
print(f"Target URL: {target_url}")
print(f"Timestamp: {datetime.now().isoformat()}")
print("\n" + "="*80 + "\n")

# ScrapingBee request
params = {
    'api_key': scrapingbee_api_key,
    'url': target_url,
    'render_js': 'true',
    'premium_proxy': 'true',
    'stealth_proxy': 'true',
    'block_resources': 'false',
    'country_code': 'us'
}

print("📤 SENDING REQUEST TO SCRAPINGBEE")
print(f"Parameters: {json.dumps({k: v for k, v in params.items() if k != 'api_key'}, indent=2)}")
print("\n" + "="*80 + "\n")

try:
    response = httpx.get("https://app.scrapingbee.com/api/v1/", params=params, timeout=60.0)
    
    # 1. Response headers + status
    print("📊 RESPONSE HEADERS + STATUS")
    print(f"Status Code: {response.status_code}")
    print(f"Reason: {response.reason_phrase}")
    print("\nHeaders:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*80 + "\n")
    
    # 2. Full HTML response
    html = response.text
    print(f"📄 FULL HTML RESPONSE ({len(html)} bytes)")
    print("\nFirst 2000 characters:")
    print(html[:2000])
    print("\n...\n")
    print("Last 1000 characters:")
    print(html[-1000:])
    
    # Save full HTML to file
    output_file = "/tmp/fastpeoplesearch_response.html"
    with open(output_file, 'w') as f:
        f.write(html)
    print(f"\n✅ Full HTML saved to: {output_file}")
    
    # Check for CloudFlare markers
    print("\n" + "="*80 + "\n")
    print("🔍 CLOUDFLARE DETECTION")
    cf_markers = [
        "cloudflare",
        "cf-browser-verification", 
        "checking your browser",
        "just a moment",
        "security challenge",
        "captcha",
        "cf-challenge-running"
    ]
    
    found_markers = [m for m in cf_markers if m in html.lower()]
    if found_markers:
        print(f"⚠️  CloudFlare markers found: {found_markers}")
    else:
        print("✅ No CloudFlare markers detected")
    
    # Check for actual content
    content_markers = [
        "fastpeoplesearch",
        "search results",
        "phone",
        "address",
        "age"
    ]
    
    found_content = [m for m in content_markers if m in html.lower()]
    print(f"\nContent markers found: {found_content}")
    
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80 + "\n")
print("✅ DIAGNOSTIC TEST COMPLETE")
print(f"View full HTML: cat /tmp/fastpeoplesearch_response.html")
