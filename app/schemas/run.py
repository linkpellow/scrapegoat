from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class RunRead(BaseModel):
    id: str
    job_id: str

    status: str
    attempt: int
    max_attempts: int

    requested_strategy: str
    resolved_strategy: str

    failure_code: Optional[str] = None
    error_message: Optional[str] = None

    stats: Dict[str, Any]
    engine_attempts: List[Dict[str, Any]] = []
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class RunEventRead(BaseModel):
    id: str
    run_id: str
    level: str
    message: str
    meta: Dict[str, Any]
    created_at: str
