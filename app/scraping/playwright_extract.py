from __future__ import annotations

from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import logging

from app.config import settings
from app.scraping.session_manager import get_session_manager

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
    browser_profile: Optional[Dict[str, Any]] = None,
    proxy_identity: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Loads the page via Playwright, then extracts fields using CSS selectors in-page.
    Returns a list of 1 record for single/detail mode.
    List-page crawling is handled by spider/worker orchestration.
    
    Session Lifecycle:
    - Attempts to reuse existing trusted session for the site
    - Creates new session if none exists or trust is low
    - Tracks success/failure to maintain session health
    
    Args:
        url: Target URL to scrape
        field_map: Field selector specifications
        session_data: Optional session cookies/storage for authenticated scraping (legacy)
        browser_profile: Optional browser fingerprint profile for stable headers
        proxy_identity: Optional proxy identifier for session keying
    """
    # Extract site domain for session management
    parsed = urlparse(url)
    site_domain = parsed.netloc
    
    # Get session manager
    session_mgr = get_session_manager()
    
    # Try to reuse existing session
    existing_session = session_mgr.get_session(site_domain, proxy_identity)
    if existing_session:
        # Use existing session cookies/storage
        session_data = {
            "cookies": existing_session.cookies,
            "storage_state": existing_session.storage_state
        }
        logger.info(f"♻️ Using existing session for {site_domain}")
    
    extraction_successful = False
    new_cookies = []
    new_storage_state = None
    
    try:
        result = _extract_with_playwright_internal(
            url, field_map, session_data, browser_profile, 
            site_domain, existing_session is not None
        )
        extraction_successful = True
        return result
    except Exception as e:
        extraction_successful = False
        raise
    finally:
        # Update session lifecycle based on result
        if extraction_successful:
            # Mark success if we reused a session
            if existing_session:
                session_mgr.mark_success(site_domain, proxy_identity)
            # Note: New session creation happens in _extract_with_playwright_internal
        else:
            # Mark failure if we reused a session
            if existing_session:
                session_mgr.mark_failure(site_domain, proxy_identity)


def _extract_with_playwright_internal(
    url: str,
    field_map: Dict[str, Dict[str, Any]],
    session_data: Optional[Dict[str, Any]],
    browser_profile: Optional[Dict[str, Any]],
    site_domain: str,
    is_reused_session: bool
) -> List[Dict[str, Any]]:
    """
    Internal Playwright extraction with session capture.
    
    Separated from extract_with_playwright to properly handle session lifecycle
    in finally block.
    """
    session_mgr = get_session_manager()
    
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
            
            // Plugin array with realistic plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ]
            });
            
            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false
                })
            });
        """)
        
        page = ctx.new_page()
        page.set_default_navigation_timeout(settings.browser_nav_timeout_ms)

        # DataDome timing: add realistic delay before navigation
        import time
        import random
        time.sleep(random.uniform(0.3, 0.8))  # Random 300-800ms delay simulates human behavior
        
        resp = page.goto(url, wait_until="networkidle")  # Wait for full page load
        status = resp.status if resp else 0

        # Basic anti-bot detection surface: if navigation fails, raise
        if status in (401, 403, 429):
            raise RuntimeError(f"blocked:Blocked (HTTP {status})")

        # Simulate human-like behavior: random small mouse movements and scrolling
        try:
            # Move mouse to random positions (simulates human looking at content)
            page.mouse.move(random.randint(100, 400), random.randint(100, 300))
            time.sleep(random.uniform(0.1, 0.3))
            
            # Small scroll down (humans often scroll a bit)
            page.evaluate("window.scrollBy(0, 100)")
            time.sleep(random.uniform(0.2, 0.5))
        except Exception:
            pass  # Not critical if this fails

        # Handle common modal checkboxes (ThatsThem, ZabaSearch FCRA agreements)
        try:
            # Wait a bit for modals to appear
            time.sleep(random.uniform(0.5, 1.0))
            
            # Try to click "I Agree" style buttons/checkboxes
            agree_selectors = [
                "#checkbox",  # ZabaSearch checkbox
                "div.verify",  # ZabaSearch verify button
                "button:has-text('I Agree')",
                "button:has-text('I AGREE')",
                "button:has-text('Accept')",
                "input[type='checkbox'][id*='agree']",
                "input[type='checkbox'][id*='consent']",
            ]
            
            for selector in agree_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=2000):
                        logger.info(f"✅ Found agreement element: {selector}, clicking...")
                        # Move mouse to element first (more human-like)
                        box = element.bounding_box()
                        if box:
                            page.mouse.move(
                                box['x'] + box['width'] / 2,
                                box['y'] + box['height'] / 2
                            )
                            time.sleep(random.uniform(0.1, 0.3))
                        element.click(timeout=2000)
                        time.sleep(random.uniform(0.5, 1.0))  # Human-like delay after click
                        # Wait for page to update after modal dismissal
                        page.wait_for_load_state("networkidle", timeout=5000)
                        break
                except Exception:
                    continue  # Try next selector
        except Exception as e:
            logger.debug(f"No modal found or already dismissed: {e}")

        # CRITICAL: Check for JSON-LD structured data (FastPeopleSearch, etc.)
        html = page.content()
        jsonld_data = _extract_jsonld_if_present(html, url)
        if jsonld_data:
            # JSON-LD found - use structured data instead of CSS selectors
            
            # Capture session state before closing (if this was a new session)
            if not is_reused_session:
                try:
                    captured_cookies = ctx.cookies()
                    captured_storage = ctx.storage_state()
                    
                    session_mgr.create_session(
                        site_domain=site_domain,
                        cookies=captured_cookies,
                        storage_state=captured_storage,
                        proxy_identity=None,
                        user_agent=context_options.get("user_agent"),
                        viewport=context_options.get("viewport")
                    )
                    logger.info(f"💾 Captured session state for {site_domain} (JSON-LD path)")
                except Exception as e:
                    logger.warning(f"Failed to capture session state: {e}")
            
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

        # Capture session state for reuse (if this was a new session)
        if not is_reused_session:
            try:
                captured_cookies = ctx.cookies()
                captured_storage = ctx.storage_state()
                
                # Store session for future reuse
                session_mgr.create_session(
                    site_domain=site_domain,
                    cookies=captured_cookies,
                    storage_state=captured_storage,
                    proxy_identity=None,  # Will be passed when proxy support added
                    user_agent=context_options.get("user_agent"),
                    viewport=context_options.get("viewport")
                )
                logger.info(f"💾 Captured session state for {site_domain} (for future reuse)")
            except Exception as e:
                logger.warning(f"Failed to capture session state: {e}")
        
        ctx.close()
        browser.close()

        return [record]
