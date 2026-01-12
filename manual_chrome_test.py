#!/usr/bin/env python3
"""
Simulate manual Chrome test - get page source as a real browser would see it
"""
from playwright.sync_api import sync_playwright
import time

target_url = "https://www.fastpeoplesearch.com/name/link-pellow_dowagiac-mi"

print(f"🌐 Fetching page as real browser: {target_url}")
print("=" * 80)

with sync_playwright() as p:
    # Launch in HEADED mode (visible browser) for maximum realism
    # If this fails on headless server, fallback to headless with max stealth
    try:
        browser = p.chromium.launch(
            headless=False,  # Real browser window
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )
        print("✅ Launched headed browser (visible)")
    except Exception:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        print("⚠️  Fallback to headless mode")
    
    # Create context with realistic fingerprint
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        timezone_id="America/New_York",
        locale="en-US",
        permissions=["geolocation"],
    )
    
    # Apply stealth scripts
    context.add_init_script("""
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Chrome object
        window.chrome = {
            runtime: {}
        };
        
        // Permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Deno.notifications }) :
                originalQuery(parameters)
        );
    """)
    
    page = context.new_page()
    
    print(f"\n📡 Navigating to: {target_url}")
    try:
        # Navigate and wait for full load
        response = page.goto(target_url, wait_until="networkidle", timeout=30000)
        
        print(f"✅ Response status: {response.status}")
        print(f"✅ Response URL: {response.url}")
        
        # Wait a bit more for JS to populate
        print("⏳ Waiting for page to fully render...")
        time.sleep(3)
        
        # Get page title
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Get full HTML
        html = page.content()
        
        # Check for Cloudflare
        if "cloudflare" in html.lower() or "just a moment" in html.lower():
            print("⚠️  CLOUDFLARE CHALLENGE DETECTED")
            print("Waiting 5 seconds for potential bypass...")
            time.sleep(5)
            html = page.content()
        
        # Check for actual content
        if "fastpeoplesearch" in html.lower():
            print("✅ FastPeopleSearch page loaded")
        
        if "link pellow" in html.lower() or "pellow" in html.lower():
            print("✅ Name found in page")
        else:
            print("⚠️  Name NOT found in page")
        
        # Save to file
        output_file = "/tmp/fastpeoplesearch_manual_chrome.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n✅ Full HTML saved to: {output_file}")
        print(f"📊 HTML size: {len(html):,} bytes")
        
        # Show first 1500 chars
        print("\n" + "=" * 80)
        print("📄 FIRST 1500 CHARACTERS:")
        print("=" * 80)
        print(html[:1500])
        print("\n...")
        
        # Show last 500 chars
        print("\n" + "=" * 80)
        print("📄 LAST 500 CHARACTERS:")
        print("=" * 80)
        print(html[-500:])
        
        # Take screenshot
        screenshot_file = "/tmp/fastpeoplesearch_screenshot.png"
        page.screenshot(path=screenshot_file, full_page=True)
        print(f"\n📸 Screenshot saved to: {screenshot_file}")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        browser.close()

print("\n" + "=" * 80)
print("✅ TEST COMPLETE")
print("\nView full HTML: cat /tmp/fastpeoplesearch_manual_chrome.html")
print("View screenshot: open /tmp/fastpeoplesearch_screenshot.png")
