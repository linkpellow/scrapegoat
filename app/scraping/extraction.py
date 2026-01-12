from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import json


def extract_jsonld_from_html(html: str, jsonld_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract JSON-LD structured data from HTML.
    
    Args:
        html: HTML content
        jsonld_type: Optional filter by @type (e.g., "Person", "Product")
    
    Returns:
        List of JSON-LD objects found
    """
    from parsel import Selector
    sel = Selector(text=html)
    
    # Find all JSON-LD script tags
    jsonld_scripts = sel.css('script[type="application/ld+json"]::text').getall()
    
    results = []
    for script_content in jsonld_scripts:
        try:
            data = json.loads(script_content)
            
            # Handle @graph wrapper
            if isinstance(data, dict) and "@graph" in data:
                items = data["@graph"]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]
            
            # Filter by type if specified
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                if jsonld_type:
                    item_type = item.get("@type", "")
                    if item_type == jsonld_type:
                        results.append(item)
                else:
                    results.append(item)
                    
        except json.JSONDecodeError:
            continue
    
    return results


def _apply_regex(value: Any, regex: Optional[str]) -> Any:
    if not regex or value is None:
        return value
    pattern = re.compile(regex)

    if isinstance(value, list):
        out: List[Any] = []
        for v in value:
            if v is None:
                continue
            m = pattern.search(str(v))
            if m:
                # Use first capture group if exists, otherwise full match
                out.append(m.group(1) if m.groups() else m.group(0))
        return out
    else:
        m = pattern.search(str(value))
        if m:
            # Use first capture group if exists, otherwise full match
            return m.group(1) if m.groups() else m.group(0)
        return None


def extract_from_html_css(html: str, spec: Dict[str, Any]) -> Any:
    """
    Pure HTML extraction (used for selector validation and browser content if needed)
    """
    from parsel import Selector
    sel = Selector(text=html)
    return extract_from_selector(sel, spec)


def extract_from_selector(sel, spec: Dict[str, Any]) -> Any:
    """
    Scrapy/Parsel-based extraction. Works for HTTP-fetched pages.
    """
    css = spec.get("css", "")
    if not css:
        return None

    attr = spec.get("attr")
    want_all = bool(spec.get("all", False))
    regex = spec.get("regex")

    if attr:
        if want_all:
            vals = [n.attrib.get(attr) for n in sel.css(css)]
            out = [v for v in vals if v]
        else:
            n = sel.css(css).get()
            if not n:
                out = None
            else:
                out = sel.css(css).attrib.get(attr)
    else:
        if want_all:
            out = [x.strip() for x in sel.css(css).xpath("normalize-space()").getall() if x and x.strip()]
        else:
            out = sel.css(css).xpath("normalize-space()").get()

    return _apply_regex(out, regex)
