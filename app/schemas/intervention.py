"""Pydantic schemas for HITL intervention tasks"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class InterventionTaskRead(BaseModel):
    """Read schema for intervention tasks"""
    id: str
    job_id: str
    run_id: Optional[str] = None
    type: str
    status: str
    trigger_reason: str
    payload: Dict[str, Any]
    resolution: Optional[Dict[str, Any]] = None
    priority: str
    expires_at: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None


class InterventionResolveRequest(BaseModel):
    """Request to resolve an intervention task"""
    resolution: Dict[str, Any] = Field(..., description="Human resolution (structured)")
    resolved_by: str = Field(default="user", description="User ID or identifier")


class InterventionListFilter(BaseModel):
    """Filter options for listing intervention tasks"""
    status: Optional[str] = None  # pending | in_progress | completed | expired
    type: Optional[str] = None    # selector_fix | field_confirm | login_refresh | manual_access
    priority: Optional[str] = None  # low | normal | high | critical
    job_id: Optional[str] = None
