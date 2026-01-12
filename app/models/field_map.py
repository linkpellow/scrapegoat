import uuid
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base


class FieldMap(Base):
    """
    Field mapping is the UI-to-engine contract.
    - For each job, define how to extract each logical field.
    - UI can generate these via click-to-map, but engine treats it as data.
    
    SmartFields V2 (backward compatible):
    - field_type: "string" (default), "email", "phone", "money", "date", "address", etc.
    - smart_config: Type-specific configuration (e.g., {"country": "US", "format": "E164"})
    - validation_rules: Validation rules (e.g., {"required": true, "min_len": 5})
    
    Backward compatibility:
    - If field_type is null/empty → defaults to "string"
    - If smart_config is null/empty → defaults to {}
    - If validation_rules is null/empty → defaults to {}
    """
    __tablename__ = "field_maps"
    __table_args__ = (UniqueConstraint("job_id", "field_name", name="uq_fieldmap_job_field"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    field_name = Column(String, nullable=False)

    # Legacy selector spec (still supported)
    # - css: "div.price"
    # - attr: "href" / "src" etc.
    # - text: true (default)
    # - regex: optional regex post-processing
    # - all: true for list extraction
    selector_spec = Column(JSONB, nullable=False, default=dict)
    
    # SmartFields V2 additions
    field_type = Column(String, nullable=False, default="string")  # FieldType enum value
    smart_config = Column(JSONB, nullable=False, default=dict)      # Type-specific config
    validation_rules = Column(JSONB, nullable=False, default=dict)  # Validation rules
    
    # Selector versioning for deterministic updates
    selector_version = Column(String, nullable=False, default="1")   # Version string (e.g., "1", "2", "3")
    selector_history = Column(JSONB, nullable=False, default=list)   # [{version, selector, updated_at, updated_by}]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
