from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List


class FieldMapUpsert(BaseModel):
    """Schema for upserting a single field map"""
    field_name: str
    selector_spec: Dict[str, Any] = Field(default_factory=dict)
    
    # SmartFields V2
    field_type: str = Field(default="string")
    smart_config: Dict[str, Any] = Field(default_factory=dict)
    validation_rules: Dict[str, Any] = Field(default_factory=dict)


class FieldMapBulkUpsert(BaseModel):
    """Schema for bulk upserting field maps"""
    mappings: List[FieldMapUpsert]


class FieldMapRead(FieldMapUpsert):
    """Schema for reading field maps"""
    id: str
    job_id: str
    created_at: str
