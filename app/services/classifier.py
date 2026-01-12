from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import httpx
from app.enums import FailureCode


@dataclass(frozen=True)
class ClassifiedFailure:
    code: FailureCode
    message: str


def classify_exception(exc: Exception) -> ClassifiedFailure:
    if isinstance(exc, httpx.TimeoutException):
        return ClassifiedFailure(FailureCode.TIMEOUT, "Request timed out")
    if isinstance(exc, httpx.NetworkError):
        return ClassifiedFailure(FailureCode.NETWORK, "Network error")
    return ClassifiedFailure(FailureCode.UNKNOWN, f"Unhandled error: {type(exc).__name__}")


def classify_http_status(status_code: int, body_snippet: Optional[str] = None) -> Optional[ClassifiedFailure]:
    # Common anti-bot / rate-limit signals
    if status_code in (401, 403):
        return ClassifiedFailure(FailureCode.BLOCKED, f"Blocked (HTTP {status_code})")
    if status_code in (429,):
        return ClassifiedFailure(FailureCode.RATE_LIMITED, f"Rate limited (HTTP {status_code})")
    if 400 <= status_code < 600:
        msg = f"Bad response (HTTP {status_code})"
        if body_snippet:
            msg += f" | snippet={body_snippet[:160]!r}"
        return ClassifiedFailure(FailureCode.BAD_RESPONSE, msg)
    return None
