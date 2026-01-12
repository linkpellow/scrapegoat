from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ExecutionStrategy, RunStatus, JobStatus
from app.models.job import Job
from app.models.run import Run
from app.models.run_event import RunEvent
from app.services.classifier import classify_http_status


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _add_event(db: Session, run_id, level: str, message: str, meta: Optional[Dict[str, Any]] = None) -> None:
    ev = RunEvent(run_id=run_id, level=level, message=message, meta=meta or {})
    db.add(ev)


async def resolve_strategy(job: Job) -> ExecutionStrategy:
    """
    Deterministic strategy resolution.
    - If job.requires_auth => BROWSER.
    - If job.strategy != AUTO => use it.
    - Else probe via HTTP. If blocked/rate-limited, escalate to BROWSER.
    - Else default HTTP.
    """
    requested = ExecutionStrategy(job.strategy)

    if job.requires_auth:
        return ExecutionStrategy.BROWSER

    if requested != ExecutionStrategy.AUTO:
        return requested

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True) as client:
        resp = await client.get(job.target_url, headers={"User-Agent": "scraper-platform/1.0"})
        body = (resp.text or "")[:400]
        failure = classify_http_status(resp.status_code, body_snippet=body)
        if failure and failure.code in ("blocked", "rate_limited"):
            return ExecutionStrategy.BROWSER

        # Lightweight JS-app heuristic (not "guessing"; it's a probe signal)
        # If the server returns a mostly-empty shell typical of SPA frameworks, use BROWSER.
        lowered = body.lower()
        spa_markers = ["__next_data__", "data-reactroot", "id=\"app\"", "window.__nuxt__"]
        if any(m in lowered for m in spa_markers):
            return ExecutionStrategy.BROWSER

    return ExecutionStrategy.HTTP


def create_run(db: Session, job: Job, resolved: ExecutionStrategy) -> Run:
    run = Run(
        job_id=job.id,
        status=RunStatus.QUEUED,
        attempt=1,
        max_attempts=settings.default_max_attempts,
        requested_strategy=job.strategy,
        resolved_strategy=resolved.value,
        stats={},
    )
    db.add(run)
    db.flush()  # assign run.id
    _add_event(db, run.id, "info", "Run created", {"resolved_strategy": resolved.value})
    return run


def mark_job_queued(db: Session, job: Job) -> None:
    job.status = JobStatus.QUEUED.value


def start_run(db: Session, run: Run) -> None:
    run.status = RunStatus.RUNNING.value
    run.started_at = _now()
    _add_event(db, run.id, "info", "Run started", {"attempt": run.attempt, "strategy": run.resolved_strategy})


def complete_run(db: Session, run: Run, stats: Dict[str, Any]) -> None:
    run.status = RunStatus.COMPLETED.value
    run.finished_at = _now()
    run.stats = stats
    _add_event(db, run.id, "info", "Run completed", {"stats": stats})
    
    # Emit run completed event (async-safe via Redis pub/sub)
    try:
        from app.services.event_emitter import emit_run_completed
        emit_run_completed(str(run.id), "completed", stats)
    except Exception:
        pass  # Don't fail the run if event emission fails


def fail_run(db: Session, run: Run, failure_code: str, error_message: str) -> None:
    run.status = RunStatus.FAILED.value
    run.finished_at = _now()
    run.failure_code = failure_code
    run.error_message = error_message
    _add_event(db, run.id, "error", "Run failed", {"failure_code": failure_code, "error_message": error_message})
    
    # Emit run failed event (async-safe via Redis pub/sub)
    try:
        from app.services.event_emitter import emit_run_failed
        emit_run_failed(str(run.id), error_message, failure_code)
    except Exception:
        pass  # Don't fail the run if event emission fails


def pause_run_for_intervention(db: Session, run: Run, reason: str, intervention_id: str) -> None:
    """
    Pause a run pending human intervention (not a failure).
    
    The run will auto-resume when the intervention is resolved.
    """
    run.status = RunStatus.WAITING_FOR_HUMAN.value
    run.error_message = f"Paused: {reason}"
    
    # Store intervention reference for auto-resume
    stats = run.stats or {}
    stats["intervention_id"] = intervention_id
    stats["paused_at"] = datetime.utcnow().isoformat()
    stats["pause_reason"] = reason
    run.stats = stats
    
    _add_event(db, run.id, "info", "Run paused for intervention", {
        "reason": reason,
        "intervention_id": intervention_id
    })
    
    # Emit paused event
    try:
        from app.services.event_emitter import emit_run_progress
        emit_run_progress(str(run.id), "paused", "waiting_for_human")
    except Exception:
        pass


def resume_run(db: Session, run: Run) -> None:
    """
    Resume a paused run after intervention resolved.
    
    Marks run as QUEUED to be picked up by worker again.
    """
    run.status = RunStatus.QUEUED.value
    run.error_message = None
    
    # Update stats
    stats = run.stats or {}
    stats["resumed_at"] = datetime.utcnow().isoformat()
    run.stats = stats
    
    _add_event(db, run.id, "info", "Run resumed after intervention", {})
    
    # Emit resumed event
    try:
        from app.services.event_emitter import emit_run_progress
        emit_run_progress(str(run.id), "resumed", "queued")
    except Exception:
        pass


def should_retry(run: Run) -> bool:
    return run.attempt < run.max_attempts


def next_backoff_seconds(attempt: int) -> int:
    # Exponential backoff with small cap; deterministic and predictable.
    # attempt=1 means first failure -> 10s, then 30s, then 90s...
    return min(300, 10 * (3 ** (attempt - 1)))


def escalate_strategy(current: str) -> str:
    # Deterministic escalation path
    if current == ExecutionStrategy.HTTP.value:
        return ExecutionStrategy.BROWSER.value
    if current == ExecutionStrategy.API_REPLAY.value:
        return ExecutionStrategy.BROWSER.value
    return current  # BROWSER stays BROWSER
