from __future__ import annotations

from typing import Any, Dict, List, Optional
import re


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
                out.append(m.group(0))
        return out
    else:
        m = pattern.search(str(value))
        return m.group(0) if m else None


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
