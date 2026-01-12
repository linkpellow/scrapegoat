from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ListWizardValidateRequest(BaseModel):
    url: str
    item_links: Dict[str, Any] = Field(..., description='Selector spec for item links, e.g. {"css":"a.title","attr":"href","all":true}')
    pagination: Optional[Dict[str, Any]] = Field(default=None, description='Selector spec for next page link, e.g. {"css":"a.next","attr":"href","all":false}')
    max_samples: int = Field(default=10, ge=1, le=50)
    prefer_browser: bool = False


class ListWizardValidateResponse(BaseModel):
    url: str
    fetched_via: str
    item_count_estimate: int
    sample_item_urls: List[str]
    next_page_url: Optional[str] = None
    warnings: List[str] = []
