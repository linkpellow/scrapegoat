from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums import JobStatus, ExecutionStrategy
from app.models.job import Job
from app.models.run import Run
from app.models.run_event import RunEvent
from app.models.record import Record
from app.models.field_map import FieldMap
from app.models.session import SessionVault
from app.schemas.job import JobCreate, JobRead
from app.schemas.run import RunRead, RunEventRead
from app.schemas.preview import PreviewRequest, PreviewResponse, SelectorValidateRequest, SelectorValidateResponse
from app.schemas.field_map import FieldMapRead, FieldMapUpsert, FieldMapBulkUpsert
from app.schemas.list_wizard import ListWizardValidateRequest, ListWizardValidateResponse
from app.services.validator import JobValidator
from app.services.orchestrator import resolve_strategy, create_run, mark_job_queued
from app.services.preview import generate_preview, validate_selector
from app.services.list_wizard import validate_list_wizard
from app.celery_app import celery_app
from fastapi.responses import StreamingResponse
from app.intelligence.adaptive_engine import get_domain_intelligence_summary
from sqlalchemy import and_
import asyncio
import json as _json

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _db() -> Session:
    return SessionLocal()


@router.get("/", response_model=list[JobRead])
def list_jobs(limit: int = 50):
    """
    List all jobs, most recent first.
    """
    db = _db()
    try:
        rows = (
            db.query(Job)
            .order_by(Job.created_at.desc())
            .limit(min(limit, 200))
            .all()
        )
        return [
            JobRead(
                id=str(j.id),
                target_url=j.target_url,
                fields=j.fields,
                requires_auth=j.requires_auth,
                frequency=j.frequency,
                strategy=ExecutionStrategy(j.strategy),
                crawl_mode=j.crawl_mode,
                list_config=j.list_config or {},
                status=j.status,
            )
            for j in rows
        ]
    finally:
        db.close()


@router.post("/", response_model=JobRead)
async def create_job(job: JobCreate):
    await JobValidator.validate_target(str(job.target_url))
    JobValidator.validate_fields(job.fields)

    db = _db()
    try:
        db_job = Job(
            target_url=str(job.target_url),
            fields=job.fields,
            requires_auth=job.requires_auth,
            frequency=job.frequency or "on_demand",
            strategy=job.strategy.value,
            status=JobStatus.VALIDATED.value,
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {},
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)

        return JobRead(
            id=str(db_job.id),
            target_url=db_job.target_url,
            fields=db_job.fields,
            requires_auth=db_job.requires_auth,
            frequency=db_job.frequency,
            strategy=ExecutionStrategy(db_job.strategy),
            status=db_job.status,
            crawl_mode=db_job.crawl_mode,
            list_config=db_job.list_config or {},
        )
    finally:
        db.close()


@router.post("/{job_id}/runs", response_model=RunRead)
async def create_job_run(job_id: str):
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        resolved = await resolve_strategy(job)
        run = create_run(db, job, resolved)
        mark_job_queued(db, job)

        db.commit()
        db.refresh(run)

        # Enqueue
        celery_app.send_task("runs.execute", args=[str(run.id)])

        return RunRead(
            id=str(run.id),
            job_id=str(run.job_id),
            status=run.status,
            attempt=run.attempt,
            max_attempts=run.max_attempts,
            requested_strategy=run.requested_strategy,
            resolved_strategy=run.resolved_strategy,
            failure_code=run.failure_code,
            error_message=run.error_message,
            stats=run.stats or {},
            engine_attempts=run.engine_attempts or [],
            created_at=run.created_at.isoformat(),
            started_at=run.started_at.isoformat() if run.started_at else None,
            finished_at=run.finished_at.isoformat() if run.finished_at else None,
        )
    finally:
        db.close()


@router.get("/{job_id}/runs", response_model=list[RunRead])
def list_job_runs(job_id: str, limit: int = 25):
    db = _db()
    try:
        runs = (
            db.query(Run)
            .filter(Run.job_id == job_id)
            .order_by(Run.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [
            RunRead(
                id=str(r.id),
                job_id=str(r.job_id),
                status=r.status,
                attempt=r.attempt,
                max_attempts=r.max_attempts,
                requested_strategy=r.requested_strategy,
                resolved_strategy=r.resolved_strategy,
                failure_code=r.failure_code,
                error_message=r.error_message,
                stats=r.stats or {},
                engine_attempts=r.engine_attempts or [],
                created_at=r.created_at.isoformat(),
                started_at=r.started_at.isoformat() if r.started_at else None,
                finished_at=r.finished_at.isoformat() if r.finished_at else None,
            )
            for r in runs
        ]
    finally:
        db.close()


@router.get("/runs", response_model=list[RunRead])
def list_all_runs(limit: int = 50, job_id: str = None, status: str = None):
    """
    List all runs across all jobs with optional filters.
    """
    db = _db()
    try:
        query = db.query(Run).order_by(Run.created_at.desc())
        
        if job_id:
            query = query.filter(Run.job_id == job_id)
        if status:
            query = query.filter(Run.status == status)
        
        runs = query.limit(min(limit, 200)).all()
        
        return [
            RunRead(
                id=str(r.id),
                job_id=str(r.job_id),
                status=r.status,
                attempt=r.attempt,
                max_attempts=r.max_attempts,
                requested_strategy=r.requested_strategy,
                resolved_strategy=r.resolved_strategy,
                failure_code=r.failure_code,
                error_message=r.error_message,
                stats=r.stats or {},
                engine_attempts=r.engine_attempts or [],
                created_at=r.created_at.isoformat(),
                started_at=r.started_at.isoformat() if r.started_at else None,
                finished_at=r.finished_at.isoformat() if r.finished_at else None,
            )
            for r in runs
        ]
    finally:
        db.close()


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: str):
    db = _db()
    try:
        r = db.query(Run).filter(Run.id == run_id).one_or_none()
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")

        return RunRead(
            id=str(r.id),
            job_id=str(r.job_id),
            status=r.status,
            attempt=r.attempt,
            max_attempts=r.max_attempts,
            requested_strategy=r.requested_strategy,
            resolved_strategy=r.resolved_strategy,
            failure_code=r.failure_code,
            error_message=r.error_message,
            stats=r.stats or {},
            created_at=r.created_at.isoformat(),
            started_at=r.started_at.isoformat() if r.started_at else None,
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
        )
    finally:
        db.close()


@router.get("/runs/{run_id}/events", response_model=list[RunEventRead])
def get_run_events(run_id: str, limit: int = 200):
    db = _db()
    try:
        events = (
            db.query(RunEvent)
            .filter(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at.asc())
            .limit(min(limit, 1000))
            .all()
        )
        return [
            RunEventRead(
                id=str(e.id),
                run_id=str(e.run_id),
                level=e.level,
                message=e.message,
                meta=e.meta or {},
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]
    finally:
        db.close()


@router.post("/preview", response_model=PreviewResponse)
def preview(req: PreviewRequest):
    data = generate_preview(str(req.url), prefer_browser=req.prefer_browser)
    return PreviewResponse(**data)


@router.post("/validate-selector", response_model=SelectorValidateResponse)
def validate_selector_api(req: SelectorValidateRequest):
    data = validate_selector(str(req.url), req.selector_spec, prefer_browser=req.prefer_browser)
    return SelectorValidateResponse(**data)


@router.post("/list-wizard/validate", response_model=ListWizardValidateResponse)
def list_wizard_validate_api(payload: ListWizardValidateRequest):
    """
    Validate list wizard selectors.
    Returns item count, sample URLs, and next page detection.
    """
    fetched_via, count, sample_urls, next_url, warnings = validate_list_wizard(
        url=payload.url,
        item_links=payload.item_links,
        pagination=payload.pagination,
        max_samples=payload.max_samples,
        prefer_browser=payload.prefer_browser,
    )
    return ListWizardValidateResponse(
        url=payload.url,
        fetched_via=fetched_via,
        item_count_estimate=count,
        sample_item_urls=sample_urls,
        next_page_url=next_url,
        warnings=warnings,
    )


@router.get("/runs/{run_id}/events/stream")
async def stream_run_events(run_id: str):
    """
    Server-Sent Events stream. UI can subscribe to live run logs.
    """
    async def event_gen():
        last_seen_ts = None
        while True:
            db = _db()
            try:
                q = db.query(RunEvent).filter(RunEvent.run_id == run_id).order_by(RunEvent.created_at.asc())
                if last_seen_ts is not None:
                    q = q.filter(RunEvent.created_at > last_seen_ts)
                events = q.limit(200).all()

                for e in events:
                    last_seen_ts = e.created_at
                    payload = {
                        "id": str(e.id),
                        "run_id": str(e.run_id),
                        "level": e.level,
                        "message": e.message,
                        "meta": e.meta or {},
                        "created_at": e.created_at.isoformat(),
                    }
                    yield f"event: run_event\ndata: {_json.dumps(payload)}\n\n"

            finally:
                db.close()

            await asyncio.sleep(0.8)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/runs/{run_id}/records")
def list_run_records(run_id: str, limit: int = 100):
    db = _db()
    try:
        rows = (
            db.query(Record)
            .filter(Record.run_id == run_id)
            .order_by(Record.created_at.asc())
            .limit(min(limit, 1000))
            .all()
        )
        return [{"id": str(r.id), "run_id": str(r.run_id), "data": r.data, "created_at": r.created_at.isoformat()} for r in rows]
    finally:
        db.close()


@router.get("/records")
def list_all_records(
    limit: int = 100,
    job_id: str = None,
    run_id: str = None,
    date_from: str = None,
    date_to: str = None,
):
    """
    List all records across all jobs with optional filters.
    """
    db = _db()
    try:
        query = db.query(Record).join(Run).order_by(Record.created_at.desc())
        
        if job_id:
            query = query.filter(Run.job_id == job_id)
        if run_id:
            query = query.filter(Record.run_id == run_id)
        if date_from:
            query = query.filter(Record.created_at >= date_from)
        if date_to:
            query = query.filter(Record.created_at <= date_to)
        
        rows = query.limit(min(limit, 1000)).all()
        
        return [
            {
                "id": str(r.id),
                "run_id": str(r.run_id),
                "data": r.data,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


@router.get("/records/stats")
def get_records_stats():
    """
    Get aggregate statistics about records.
    """
    db = _db()
    try:
        from sqlalchemy import func
        
        # Total records
        total = db.query(func.count(Record.id)).scalar() or 0
        
        # Records by job
        by_job = (
            db.query(Job.id, Job.target_url, func.count(Record.id).label("count"))
            .join(Run, Run.job_id == Job.id)
            .join(Record, Record.run_id == Run.id)
            .group_by(Job.id, Job.target_url)
            .all()
        )
        
        # Recent growth (last 7 days)
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = (
            db.query(func.count(Record.id))
            .filter(Record.created_at >= seven_days_ago)
            .scalar() or 0
        )
        
        return {
            "total_records": total,
            "by_job": [
                {
                    "job_id": str(job_id),
                    "job_url": url,
                    "record_count": count,
                }
                for job_id, url, count in by_job
            ],
            "last_7_days": recent,
        }
    finally:
        db.close()


@router.delete("/records/{record_id}")
def delete_record(record_id: str):
    """
    Delete a specific record.
    """
    db = _db()
    try:
        record = db.query(Record).filter(Record.id == record_id).one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        
        db.delete(record)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


# Sessions endpoints
@router.get("/sessions")
def list_sessions():
    """
    List all stored sessions.
    """
    db = _db()
    try:
        sessions = db.query(SessionVault).all()
        return [
            {
                "id": str(s.id),
                "job_id": str(s.job_id),
                "has_cookies": "cookies" in (s.session_data or {}),
                "has_storage": "storage" in (s.session_data or {}),
                "cookie_count": len((s.session_data or {}).get("cookies", [])),
            }
            for s in sessions
        ]
    finally:
        db.close()


@router.post("/sessions")
def create_session(payload: dict):
    """
    Create or update a session for a job.
    Expected payload: { "job_id": "...", "session_data": {...} }
    """
    db = _db()
    try:
        job_id = payload.get("job_id")
        session_data = payload.get("session_data", {})
        
        if not job_id:
            raise HTTPException(status_code=400, detail="job_id required")
        
        # Check if job exists
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Find or create session
        existing = db.query(SessionVault).filter(SessionVault.job_id == job_id).one_or_none()
        
        if existing:
            existing.session_data = session_data
            db.commit()
            db.refresh(existing)
            return {"id": str(existing.id), "job_id": str(existing.job_id), "ok": True}
        else:
            session = SessionVault(job_id=job_id, session_data=session_data)
            db.add(session)
            db.commit()
            db.refresh(session)
            return {"id": str(session.id), "job_id": str(session.job_id), "ok": True}
    finally:
        db.close()


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """
    Delete a session.
    """
    db = _db()
    try:
        session = db.query(SessionVault).filter(SessionVault.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        db.delete(session)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/sessions/{session_id}/validate")
def validate_session(session_id: str):
    """
    Validate if a session is still valid (placeholder).
    In production, this would test the cookies/storage against the target site.
    """
    db = _db()
    try:
        session = db.query(SessionVault).filter(SessionVault.id == session_id).one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Placeholder validation - in production, this would make a test request
        has_cookies = "cookies" in (session.session_data or {})
        cookie_count = len((session.session_data or {}).get("cookies", []))
        
        return {
            "valid": has_cookies and cookie_count > 0,
            "message": f"Session has {cookie_count} cookies" if has_cookies else "No cookies found",
        }
    finally:
        db.close()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str):
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return JobRead(
            id=str(job.id),
            target_url=job.target_url,
            fields=job.fields,
            requires_auth=job.requires_auth,
            frequency=job.frequency,
            strategy=ExecutionStrategy(job.strategy),
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {},
            status=job.status,
        )
    finally:
        db.close()


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: str, payload: dict):
    """
    Allows updating:
    - fields
    - crawl_mode
    - list_config
    - requires_auth
    """
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        allowed = {"fields", "crawl_mode", "list_config", "requires_auth"}
        for k, v in payload.items():
            if k in allowed:
                setattr(job, k, v)

        db.commit()
        db.refresh(job)

        return JobRead(
            id=str(job.id),
            target_url=job.target_url,
            fields=job.fields,
            requires_auth=job.requires_auth,
            frequency=job.frequency,
            strategy=ExecutionStrategy(job.strategy),
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {},
            status=job.status,
        )
    finally:
        db.close()


@router.get("/{job_id}/field-maps", response_model=list[FieldMapRead])
def list_field_maps(job_id: str):
    db = _db()
    try:
        rows = (
            db.query(FieldMap)
            .filter(FieldMap.job_id == job_id)
            .order_by(FieldMap.created_at.asc())
            .all()
        )
        return [
            FieldMapRead(
                id=str(r.id),
                job_id=str(r.job_id),
                field_name=r.field_name,
                selector_spec=r.selector_spec or {},
                field_type=r.field_type or "string",
                smart_config=r.smart_config or {},
                validation_rules=r.validation_rules or {},
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ]
    finally:
        db.close()


@router.put("/{job_id}/field-maps", response_model=list[FieldMapRead])
def bulk_upsert_field_maps(job_id: str, payload: FieldMapBulkUpsert):
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        out_rows: list[FieldMap] = []

        for m in payload.mappings:
            existing = (
                db.query(FieldMap)
                .filter(and_(FieldMap.job_id == job_id, FieldMap.field_name == m.field_name))
                .one_or_none()
            )

            if existing:
                existing.selector_spec = m.selector_spec or {}
                existing.field_type = getattr(m, 'field_type', 'string')
                existing.smart_config = getattr(m, 'smart_config', {})
                existing.validation_rules = getattr(m, 'validation_rules', {})
                out_rows.append(existing)
            else:
                row = FieldMap(
                    job_id=job_id,
                    field_name=m.field_name,
                    selector_spec=m.selector_spec or {},
                    field_type=getattr(m, 'field_type', 'string'),
                    smart_config=getattr(m, 'smart_config', {}),
                    validation_rules=getattr(m, 'validation_rules', {})
                )
                db.add(row)
                db.flush()
                out_rows.append(row)

        db.commit()

        return [
            FieldMapRead(
                id=str(r.id),
                job_id=str(r.job_id),
                field_name=r.field_name,
                selector_spec=r.selector_spec or {},
                field_type=r.field_type or "string",
                smart_config=r.smart_config or {},
                validation_rules=r.validation_rules or {},
                created_at=r.created_at.isoformat(),
            )
            for r in out_rows
        ]
    finally:
        db.close()


@router.post("/{job_id}/field-maps/validate")
def bulk_validate_field_maps(job_id: str, payload: FieldMapBulkUpsert):
    """
    Validate all field mappings in bulk without saving them.
    Returns validation results for each field.
    """
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        results = []
        for m in payload.mappings:
            r = validate_selector(
                job.target_url,
                m.selector_spec,
                prefer_browser=job.strategy == "browser"
            )
            results.append({
                "field_name": m.field_name,
                "result": r
            })

        return results
    finally:
        db.close()


@router.post("/{job_id}/clone", response_model=JobRead)
def clone_job(job_id: str):
    """
    Clone an existing job with all its field mappings.
    """
    db = _db()
    try:
        job = db.query(Job).filter(Job.id == job_id).one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Create new job with same config
        new_job = Job(
            id=uuid.uuid4(),
            target_url=job.target_url,
            fields=job.fields,
            requires_auth=job.requires_auth,
            frequency=job.frequency,
            strategy=job.strategy,
            status=JobStatus.VALIDATED.value,
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {},
        )
        db.add(new_job)
        db.flush()
        
        # Clone field mappings
        field_maps = db.query(FieldMap).filter(FieldMap.job_id == job_id).all()
        for fm in field_maps:
            new_fm = FieldMap(
                job_id=new_job.id,
                field_name=fm.field_name,
                selector_spec=fm.selector_spec,
            )
            db.add(new_fm)
        
        db.commit()
        db.refresh(new_job)
        
        return JobRead(
            id=str(new_job.id),
            target_url=new_job.target_url,
            fields=new_job.fields,
            requires_auth=new_job.requires_auth,
            frequency=new_job.frequency,
            strategy=ExecutionStrategy(new_job.strategy),
            status=new_job.status,
            crawl_mode=new_job.crawl_mode,
            list_config=new_job.list_config or {},
        )
    finally:
        db.close()


@router.delete("/{job_id}/field-maps/{field_name}")
def delete_field_map(job_id: str, field_name: str):
    db = _db()
    try:
        row = (
            db.query(FieldMap)
            .filter(and_(FieldMap.job_id == job_id, FieldMap.field_name == field_name))
            .one_or_none()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Field map not found")

        db.delete(row)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.get("/intelligence/domain")
def get_domain_intelligence(url: str):
    """
    Get adaptive intelligence summary for a domain.
    
    Returns historical performance stats per engine for the given URL's domain.
    This shows what the adaptive intelligence layer has learned.
    """
    db = _db()
    try:
        summary = get_domain_intelligence_summary(db, url)
        return summary
    finally:
        db.close()
