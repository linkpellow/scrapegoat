"""
Selector versioning for deterministic HITL updates

When humans fix selectors via HITL:
- New selector version is created
- Old selector preserved in history
- All future runs use new version
- Historical data remains unchanged

This ensures:
- No silent mutation
- Full audit trail
- Rollback capability
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.field_map import FieldMap


def update_selector(
    db: Session,
    field_map_id: str,
    new_selector: str,
    updated_by: str = "system"
) -> FieldMap:
    """
    Update a field map's selector with versioning.
    
    Args:
        db: Database session
        field_map_id: FieldMap ID
        new_selector: New selector spec
        updated_by: User ID or system identifier
    
    Returns:
        Updated FieldMap
    """
    field_map = db.query(FieldMap).filter(FieldMap.id == field_map_id).one_or_none()
    if not field_map:
        raise ValueError(f"FieldMap {field_map_id} not found")
    
    # Get current version
    current_version = int(field_map.selector_version)
    new_version = str(current_version + 1)
    
    # Add current selector to history
    history_entry = {
        "version": field_map.selector_version,
        "selector": field_map.selector_spec,
        "updated_at": datetime.now().isoformat(),
        "updated_by": updated_by
    }
    
    history = field_map.selector_history or []
    history.append(history_entry)
    
    # Update to new selector
    field_map.selector_spec = new_selector
    field_map.selector_version = new_version
    field_map.selector_history = history
    
    return field_map


def get_selector_history(
    db: Session,
    field_map_id: str
) -> list:
    """
    Get selector version history for a field map.
    
    Args:
        db: Database session
        field_map_id: FieldMap ID
    
    Returns:
        List of history entries
    """
    field_map = db.query(FieldMap).filter(FieldMap.id == field_map_id).one_or_none()
    if not field_map:
        return []
    
    return field_map.selector_history or []


def rollback_selector(
    db: Session,
    field_map_id: str,
    target_version: str
) -> Optional[FieldMap]:
    """
    Rollback selector to a previous version.
    
    Args:
        db: Database session
        field_map_id: FieldMap ID
        target_version: Version to rollback to
    
    Returns:
        Updated FieldMap or None if version not found
    """
    field_map = db.query(FieldMap).filter(FieldMap.id == field_map_id).one_or_none()
    if not field_map:
        return None
    
    history = field_map.selector_history or []
    target_entry = next((h for h in history if h["version"] == target_version), None)
    
    if not target_entry:
        return None
    
    # Create new version entry for rollback
    rollback_entry = {
        "version": field_map.selector_version,
        "selector": field_map.selector_spec,
        "updated_at": datetime.now().isoformat(),
        "updated_by": "system_rollback",
        "rollback_to": target_version
    }
    
    history.append(rollback_entry)
    
    # Apply rollback
    field_map.selector_spec = target_entry["selector"]
    field_map.selector_version = str(int(field_map.selector_version) + 1)  # Still increment version
    field_map.selector_history = history
    
    return field_map
