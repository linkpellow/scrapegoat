#!/usr/bin/env python3
"""
Test JSON-LD extraction from the actual FastPeopleSearch page
"""
from app.scraping.extraction import extract_jsonld_from_html
from playwright.sync_api import sync_playwright
import json

target_url = "https://www.fastpeoplesearch.com/name/link-pellow_dowagiac-mi"

print(f"🎯 Testing JSON-LD extraction for: {target_url}")
print("=" * 80)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
    )
    
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        timezone_id="America/New_York",
        locale="en-US",
    )
    
    # Add stealth
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)
    
    page = context.new_page()
    
    print("📡 Navigating...")
    try:
        response = page.goto(target_url, wait_until="networkidle", timeout=45000)
        print(f"✅ Status: {response.status}")
        
        # Get HTML
        html = page.content()
        print(f"📄 HTML size: {len(html):,} bytes")
        
        # Extract JSON-LD
        print("\n" + "=" * 80)
        print("🔍 Extracting JSON-LD Person objects...")
        
        person_objects = extract_jsonld_from_html(html, jsonld_type="Person")
        
        if person_objects:
            print(f"✅ Found {len(person_objects)} Person objects\n")
            
            for i, person in enumerate(person_objects, 1):
                print(f"\n📋 Person {i}:")
                print(json.dumps(person, indent=2))
                
                # Extract key fields
                print(f"\n  Name: {person.get('name')}")
                
                phones = person.get('telephone', [])
                if isinstance(phones, str):
                    phones = [phones]
                print(f"  Phones: {phones}")
                
                location = person.get('HomeLocation') or {}
                if location:
                    print(f"  Address: {location.get('streetAddress')}")
                    print(f"  City: {location.get('addressLocality')}")
                    print(f"  State: {location.get('addressRegion')}")
                    print(f"  Zip: {location.get('postalCode')}")
                
                print("  " + "-" * 60)
        else:
            print("❌ No JSON-LD Person objects found")
            
            # Check what JSON-LD is present
            all_jsonld = extract_jsonld_from_html(html)
            if all_jsonld:
                print(f"\n⚠️  Found {len(all_jsonld)} other JSON-LD objects:")
                for obj in all_jsonld:
                    print(f"    - {obj.get('@type', 'Unknown')}")
            else:
                print("\n❌ No JSON-LD found at all")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        browser.close()

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
