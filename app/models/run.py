import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    status = Column(String, nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False)

    requested_strategy = Column(String, nullable=False)
    resolved_strategy = Column(String, nullable=False)

    failure_code = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    stats = Column(JSONB, nullable=False, default=dict)

    # Auto-escalation attempt log
    # [
    #   {
    #     "engine": "http",
    #     "status": 200,
    #     "signals": ["nextjs_detected"],
    #     "decision": "escalate:js_app",
    #     "timestamp": "2026-01-12T01:50:00Z"
    #   },
    #   ...
    # ]
    engine_attempts = Column(JSONB, nullable=False, default=list, server_default='[]')

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
