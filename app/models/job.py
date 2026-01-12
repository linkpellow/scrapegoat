import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_url = Column(String, nullable=False)
    fields = Column(JSONB, nullable=False)  # list[str]
    requires_auth = Column(Boolean, default=False, nullable=False)
    frequency = Column(String, nullable=False)
    strategy = Column(String, nullable=False)
    status = Column(String, nullable=False)

    # Step Four additions
    # crawl_mode: "single" (default) or "list"
    crawl_mode = Column(String, nullable=False, default="single")

    # list_config example:
    # {
    #   "item_links": {"css": "a.product", "attr": "href", "all": true},
    #   "pagination": {"css": "a.next", "attr": "href", "all": false},
    #   "max_pages": 5,
    #   "max_items": 200,
    #   "allowed_domains": ["example.com"]
    # }
    list_config = Column(JSONB, nullable=False, default=dict)

    # Auto-escalation engine mode
    # "auto" (default) = intelligent escalation, "http" = force HTTP only,
    # "playwright" = force browser, "provider" = force external provider
    engine_mode = Column(String, nullable=False, default="auto")

    # Browser fingerprint profile for Playwright stability
    # {
    #   "user_agent": "...",
    #   "viewport": {"width": 1920, "height": 1080},
    #   "timezone": "America/New_York",
    #   "locale": "en-US",
    #   "accept_language": "en-US,en;q=0.9"
    # }
    browser_profile = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
