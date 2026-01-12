from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, List, Optional


class PreviewRequest(BaseModel):
    url: HttpUrl
    prefer_browser: bool = False


class PreviewResponse(BaseModel):
    url: str
    fetched_via: str  # "http" | "browser"
    html_snippet: str
    suggestions: List[Dict[str, Any]]  # e.g. [{"label":"title", "css":"h1", "confidence":0.8}]


class SelectorValidateRequest(BaseModel):
    url: HttpUrl
    selector_spec: Dict[str, Any]
    prefer_browser: bool = False


class SelectorValidateResponse(BaseModel):
    url: str
    fetched_via: str
    selector_spec: Dict[str, Any]
    value_preview: Any
    match_count_estimate: int
