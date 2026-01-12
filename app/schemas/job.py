from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from app.enums import ExecutionStrategy


class JobCreate(BaseModel):
    target_url: HttpUrl
    fields: List[str] = Field(..., min_length=1)
    requires_auth: bool = False
    frequency: Optional[str] = "on_demand"
    strategy: ExecutionStrategy = ExecutionStrategy.AUTO

    # Step Four
    crawl_mode: str = Field(default="single", pattern="^(single|list)$")
    list_config: Dict[str, Any] = Field(default_factory=dict)

    # Auto-escalation engine
    engine_mode: str = Field(default="auto", pattern="^(auto|http|playwright|provider)$")
    browser_profile: Dict[str, Any] = Field(default_factory=dict)


class JobRead(JobCreate):
    id: str
    status: str
