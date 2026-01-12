from enum import Enum


class JobStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"  # Paused, needs intervention
    FAILED = "failed"
    COMPLETED = "completed"


class ExecutionStrategy(str, Enum):
    AUTO = "auto"
    HTTP = "http"
    BROWSER = "browser"
    API_REPLAY = "api_replay"


class FailureCode(str, Enum):
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    NETWORK = "network"
    BAD_RESPONSE = "bad_response"
    UNKNOWN = "unknown"


class DomainAccessClass(str, Enum):
    """
    Classification of how a domain must be accessed.
    
    PUBLIC: No auth required, standard scraping works
    INFRA: Requires infrastructure (proxies, providers)
    HUMAN: Requires human session (HITL mandatory)
    """
    PUBLIC = "public"
    INFRA = "infra"  # Needs proxies/providers
    HUMAN = "human"  # Needs HITL session


class SessionHealthStatus(str, Enum):
    """Health status of a stored session."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"
    EXPIRED = "expired"
