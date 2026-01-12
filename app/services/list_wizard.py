from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from app.services.preview import _http_get, _browser_get


def _extract_links(base_url: str, html: str, spec: Dict[str, Any]) -> List[str]:
    """
    Extract links from HTML using a selector spec.
    Returns absolute URLs, deduplicated while preserving order.
    """
    css = spec.get("css", "")
    attr = spec.get("attr") or "href"
    want_all = bool(spec.get("all", True))
    
    if not css:
        return []

    soup = BeautifulSoup(html, "lxml")
    els = soup.select(css)
    
    if not els:
        return []

    urls: List[str] = []
    for el in (els if want_all else els[:1]):
        val = el.get(attr)
        if not val:
            continue
        urls.append(urljoin(base_url, val))

    # Deduplicate, preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    
    return out


def validate_list_wizard(
    url: str,
    item_links: Dict[str, Any],
    pagination: Optional[Dict[str, Any]],
    max_samples: int,
    prefer_browser: bool,
) -> Tuple[str, int, List[str], Optional[str], List[str]]:
    """
    Validate list wizard selectors against a page.
    
    Returns:
        - fetched_via: "http" or "browser"
        - item_count_estimate: number of items matched
        - sample_item_urls: list of sample item URLs (up to max_samples)
        - next_url: URL of next page (if pagination selector matched)
        - warnings: list of warning messages
    """
    warnings: List[str] = []

    # Fetch HTML
    if prefer_browser:
        fetched_via, html = _browser_get(url)
    else:
        fetched_via, html = _http_get(url)

    # Extract item links
    item_urls = _extract_links(url, html, item_links)
    
    if not item_urls:
        warnings.append("No item links matched. Check the item link selector.")
        item_count_estimate = 0
        sample_item_urls = []
    else:
        item_count_estimate = len(item_urls)
        sample_item_urls = item_urls[:max_samples]

    # Extract next page link
    next_url: Optional[str] = None
    if pagination:
        next_urls = _extract_links(url, html, {**pagination, "all": False})
        next_url = next_urls[0] if next_urls else None
        if not next_url:
            warnings.append("Next page selector did not match a link with href.")

    return fetched_via, item_count_estimate, sample_item_urls, next_url, warnings
