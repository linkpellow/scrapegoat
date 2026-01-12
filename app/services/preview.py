from __future__ import annotations

from typing import Dict, Any, List, Tuple
import httpx
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from app.config import settings
from app.services.classifier import classify_http_status


def _http_get(url: str) -> Tuple[str, str]:
    with httpx.Client(timeout=settings.http_timeout_seconds, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": "scraper-platform/1.0"})
        snippet = (r.text or "")[:500]
        failure = classify_http_status(r.status_code, body_snippet=snippet)
        if failure and failure.code.value in ("blocked", "rate_limited"):
            raise RuntimeError(f"{failure.code.value}:{failure.message}")
        return "http", (r.text or "")


def _browser_get(url: str) -> Tuple[str, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent="scraper-platform/1.0")
        page = ctx.new_page()
        page.set_default_navigation_timeout(settings.browser_nav_timeout_ms)
        resp = page.goto(url, wait_until="domcontentloaded")
        html = page.content()
        status = resp.status if resp else 0
        ctx.close()
        browser.close()

        failure = classify_http_status(status, body_snippet=(html or "")[:500])
        if failure and failure.code.value in ("blocked", "rate_limited"):
            raise RuntimeError(f"{failure.code.value}:{failure.message}")
        return "browser", (html or "")


def _suggest_fields(html: str) -> List[Dict[str, Any]]:
    """
    Minimal, deterministic heuristics:
    - title: h1 or title tag
    - price: common price patterns
    - links: a[href] count suggests list pages
    This is deliberately conservative; UI click-to-map will refine.
    """
    soup = BeautifulSoup(html, "lxml")

    suggestions: List[Dict[str, Any]] = []

    h1 = soup.select_one("h1")
    if h1 and h1.get_text(strip=True):
        suggestions.append({"label": "title", "css": "h1", "confidence": 0.75})

    title = soup.title.get_text(strip=True) if soup.title else ""
    if title:
        suggestions.append({"label": "document_title", "css": "title", "confidence": 0.55})

    price_nodes = soup.select("[class*=price], [id*=price], [data-testid*=price]")
    if price_nodes:
        suggestions.append({"label": "price", "css": "[class*=price], [id*=price], [data-testid*=price]", "confidence": 0.45})

    return suggestions


def generate_preview(url: str, prefer_browser: bool = False) -> Dict[str, Any]:
    try:
        if prefer_browser:
            via, html = _browser_get(url)
        else:
            via, html = _http_get(url)
    except RuntimeError:
        # escalate to browser if HTTP got blocked / rate limited
        via, html = _browser_get(url)

    snippet = html[:6000]  # UI preview should never store full page in DB at this stage
    suggestions = _suggest_fields(html)

    return {
        "url": url,
        "fetched_via": via,
        "html_snippet": snippet,
        "suggestions": suggestions,
    }


def validate_selector(url: str, selector_spec: Dict[str, Any], prefer_browser: bool = False) -> Dict[str, Any]:
    """
    Validates a selector against a page and returns preview of extracted value.
    Used by UI to test selectors before saving to FieldMap.
    """
    from app.scraping.extraction import extract_from_html_css
    
    data = generate_preview(url, prefer_browser=prefer_browser)
    html = data["html_snippet"]
    via = data["fetched_via"]

    # Estimate matches count using parsel
    from parsel import Selector
    sel = Selector(text=html)
    css = selector_spec.get("css", "")
    count = len(sel.css(css)) if css else 0

    value = extract_from_html_css(html, selector_spec)

    return {
        "url": url,
        "fetched_via": via,
        "selector_spec": selector_spec,
        "value_preview": value,
        "match_count_estimate": count,
    }
