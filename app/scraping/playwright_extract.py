from __future__ import annotations

from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright

from app.config import settings


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
        browser = p.chromium.launch(headless=True)
        
        # Build context options with browser profile
        context_options = {}
        
        if browser_profile:
            context_options["user_agent"] = browser_profile.get("user_agent", "scraper-platform/2.0")
            if "viewport" in browser_profile:
                context_options["viewport"] = browser_profile["viewport"]
            if "timezone" in browser_profile:
                context_options["timezone_id"] = browser_profile["timezone"]
            if "locale" in browser_profile:
                context_options["locale"] = browser_profile["locale"]
            if "accept_language" in browser_profile:
                # Set via extra_http_headers
                context_options.setdefault("extra_http_headers", {})
                context_options["extra_http_headers"]["Accept-Language"] = browser_profile["accept_language"]
        else:
            context_options["user_agent"] = "scraper-platform/1.0"
        
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
        
        page = ctx.new_page()
        page.set_default_navigation_timeout(settings.browser_nav_timeout_ms)

        resp = page.goto(url, wait_until="domcontentloaded")
        status = resp.status if resp else 0

        # Basic anti-bot detection surface: if navigation fails, raise
        if status in (401, 403, 429):
            raise RuntimeError(f"blocked:Blocked (HTTP {status})")

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
