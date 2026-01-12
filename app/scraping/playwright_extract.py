from __future__ import annotations

from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_jsonld_if_present(html: str, url: str) -> Optional[List[Dict[str, Any]]]:
    """
    Check if page contains JSON-LD structured data and extract it.
    Returns None if no usable JSON-LD found.
    
    For FastPeopleSearch, extracts Person objects with phones, addresses, etc.
    """
    from app.scraping.extraction import extract_jsonld_from_html
    
    # Check for JSON-LD Person objects (people search sites)
    person_objects = extract_jsonld_from_html(html, jsonld_type="Person")
    
    if not person_objects:
        return None
    
    logger.info(f"✅ Found {len(person_objects)} JSON-LD Person objects")
    
    # Transform JSON-LD to our record format
    records = []
    for person in person_objects:
        record = {
            "_meta": {"url": url, "engine": "playwright", "source": "jsonld"},
            "name": person.get("name"),
        }
        
        # Extract phones
        telephones = person.get("telephone", [])
        if isinstance(telephones, str):
            telephones = [telephones]
        if telephones:
            record["phone"] = telephones
        
        # Extract address
        home_location = person.get("HomeLocation") or person.get("homeLocation") or {}
        if home_location:
            address_parts = []
            if home_location.get("streetAddress"):
                address_parts.append(home_location["streetAddress"])
            if home_location.get("addressLocality"):
                address_parts.append(home_location["addressLocality"])
            if home_location.get("addressRegion"):
                address_parts.append(home_location["addressRegion"])
            if home_location.get("postalCode"):
                address_parts.append(home_location["postalCode"])
            
            if address_parts:
                record["address"] = ", ".join(address_parts)
                record["city"] = home_location.get("addressLocality")
                record["state"] = home_location.get("addressRegion")
                record["zip"] = home_location.get("postalCode")
        
        # Extract age (if present)
        if "age" in person:
            record["age"] = person["age"]
        
        # Extract relatives
        relatives = person.get("relatedTo", [])
        if relatives:
            if isinstance(relatives, list):
                record["relatives"] = [r.get("name") for r in relatives if isinstance(r, dict) and "name" in r]
            elif isinstance(relatives, dict):
                record["relatives"] = [relatives.get("name")]
        
        records.append(record)
    
    logger.info(f"✅ Extracted {len(records)} enriched records from JSON-LD")
    return records


def extract_with_playwright(
    url: str,
    field_map: Dict[str, Dict[str, Any]],
    session_data: Optional[Dict[str, Any]] = None,
    browser_profile: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Loads the page via Playwright, then extracts fields using CSS selectors in-page.
    Returns a list of 1 record for single/detail mode.
    List-page crawling is handled by spider/worker orchestration.
    
    Args:
        url: Target URL to scrape
        field_map: Field selector specifications
        session_data: Optional session cookies/storage for authenticated scraping
        browser_profile: Optional browser fingerprint profile for stable headers
    """
    with sync_playwright() as p:
        # DataDome-aware configuration (NOT Cloudflare)
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                # DataDome fingerprinting mitigation
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ]
        )
        
        # Build context options with browser profile (DataDome-aware)
        context_options = {}
        
        if browser_profile:
            context_options["user_agent"] = browser_profile.get("user_agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            if "viewport" in browser_profile:
                context_options["viewport"] = browser_profile["viewport"]
            if "timezone_id" in browser_profile:
                context_options["timezone_id"] = browser_profile["timezone_id"]
            if "locale" in browser_profile:
                context_options["locale"] = browser_profile["locale"]
            if "permissions" in browser_profile:
                context_options["permissions"] = browser_profile["permissions"]
            if "color_scheme" in browser_profile:
                context_options["color_scheme"] = browser_profile["color_scheme"]
            if "reduced_motion" in browser_profile:
                context_options["reduced_motion"] = browser_profile["reduced_motion"]
            if "forced_colors" in browser_profile:
                context_options["forced_colors"] = browser_profile["forced_colors"]
        else:
            context_options["user_agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Apply session data if provided
        if session_data:
            storage_state = session_data.get("storage_state")
            cookies = session_data.get("cookies", [])
            
            if storage_state:
                context_options["storage_state"] = storage_state
                ctx = browser.new_context(**context_options)
            else:
                ctx = browser.new_context(**context_options)
                if cookies:
                    ctx.add_cookies(cookies)
        else:
            ctx = browser.new_context(**context_options)
        
        # DataDome evasion: stealth scripts
        ctx.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Add chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Fix permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: 'prompt' }) :
                    originalQuery(parameters)
            );
            
            // Plugin array
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        page = ctx.new_page()
        page.set_default_navigation_timeout(settings.browser_nav_timeout_ms)

        # DataDome timing: add realistic delay before navigation
        import time
        time.sleep(0.5)  # 500ms delay simulates human behavior
        
        resp = page.goto(url, wait_until="networkidle")  # Wait for full page load
        status = resp.status if resp else 0

        # Basic anti-bot detection surface: if navigation fails, raise
        if status in (401, 403, 429):
            raise RuntimeError(f"blocked:Blocked (HTTP {status})")

        # CRITICAL: Check for JSON-LD structured data (FastPeopleSearch, etc.)
        html = page.content()
        jsonld_data = _extract_jsonld_if_present(html, url)
        if jsonld_data:
            # JSON-LD found - use structured data instead of CSS selectors
            ctx.close()
            browser.close()
            return jsonld_data

        record: Dict[str, Any] = {"_meta": {"url": url, "status": status, "engine": "playwright"}}

        for field_name, spec in field_map.items():
            css = spec.get("css", "")
            if not css:
                record[field_name] = None
                continue

            attr = spec.get("attr")
            want_all = bool(spec.get("all", False))

            if want_all:
                loc = page.locator(css)
                count = loc.count()
                vals: List[Any] = []
                for i in range(count):
                    el = loc.nth(i)
                    if attr:
                        v = el.get_attribute(attr)
                    else:
                        v = el.inner_text()
                    if v is not None:
                        v = v.strip()
                    if v:
                        vals.append(v)
                record[field_name] = vals
            else:
                loc = page.locator(css).first
                if attr:
                    v = loc.get_attribute(attr)
                else:
                    v = loc.inner_text()
                if v is not None:
                    v = v.strip()
                record[field_name] = v or None

        ctx.close()
        browser.close()

        return [record]
