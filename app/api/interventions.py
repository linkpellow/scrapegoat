"""
Intervention API - HITL management endpoints.

Endpoints:
- GET /interventions - List all interventions
- GET /interventions/{id} - Get intervention details
- POST /interventions/{id}/resolve - Mark intervention as resolved
- POST /interventions/{id}/capture-session - Capture session for intervention
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.database import SessionLocal
from app.models.intervention import InterventionTask
from app.models.session import SessionVault
from app.models.run import Run
from app.services.orchestrator import resume_run
from app.services.event_emitter import emit_intervention_resolved
import uuid

router = APIRouter()


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class InterventionResponse(BaseModel):
    id: str
    type: str
    status: str
    trigger_reason: str
    priority: str
    job_id: str
    run_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: str
    resolved_at: Optional[str] = None


class ResolveInterventionRequest(BaseModel):
    resolution: Dict[str, Any]
    resolved_by: str
    captured_session: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[InterventionResponse])
def list_interventions(
    status: Optional[str] = "pending",
    db: Session = Depends(_db)
):
    """List interventions, optionally filtered by status."""
    query = db.query(InterventionTask)
    
    if status:
        query = query.filter(InterventionTask.status == status)
    
    interventions = query.order_by(InterventionTask.created_at.desc()).limit(100).all()
    
    return [
        InterventionResponse(
            id=str(i.id),
            type=i.type,
            status=i.status,
            trigger_reason=i.trigger_reason,
            priority=i.priority,
            job_id=str(i.job_id),
            run_id=str(i.run_id) if i.run_id else None,
            payload=i.payload,
            created_at=i.created_at.isoformat(),
            resolved_at=i.resolved_at.isoformat() if i.resolved_at else None
        )
        for i in interventions
    ]


@router.get("/{intervention_id}", response_model=InterventionResponse)
def get_intervention(intervention_id: str, db: Session = Depends(_db)):
    """Get intervention details."""
    intervention = db.query(InterventionTask).filter(
        InterventionTask.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    return InterventionResponse(
        id=str(intervention.id),
        type=intervention.type,
        status=intervention.status,
        trigger_reason=intervention.trigger_reason,
        priority=intervention.priority,
        job_id=str(intervention.job_id),
        run_id=str(intervention.run_id) if intervention.run_id else None,
        payload=intervention.payload,
        created_at=intervention.created_at.isoformat(),
        resolved_at=intervention.resolved_at.isoformat() if intervention.resolved_at else None
    )


@router.post("/{intervention_id}/resolve")
def resolve_intervention(
    intervention_id: str,
    request: ResolveInterventionRequest,
    db: Session = Depends(_db)
):
    """
    Mark intervention as resolved and resume paused run.
    
    If captured_session provided, saves to SessionVault.
    """
    intervention = db.query(InterventionTask).filter(
        InterventionTask.id == intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    if intervention.status == "resolved":
        raise HTTPException(status_code=400, detail="Intervention already resolved")
    
    # Mark as resolved
    intervention.status = "resolved"
    intervention.resolved_at = datetime.utcnow()
    intervention.resolution = request.resolution
    intervention.resolved_by = request.resolved_by
    
    # Save captured session if provided
    if request.captured_session:
        domain = intervention.payload.get("domain")
        
        if domain:
            session = SessionVault(
                id=str(uuid.uuid4()),
                domain=domain,
                session_data=request.captured_session,
                captured_at=datetime.utcnow(),
                last_validated=datetime.utcnow(),
                is_valid=True,
                health_status="valid",
                intervention_id=uuid.UUID(intervention_id),
                notes=f"Captured via intervention resolution: {intervention.trigger_reason}"
            )
            db.add(session)
    
    db.commit()
    
    # Emit resolved event
    emit_intervention_resolved(intervention_id, request.resolution)
    
    # AUTO-RESUME: If run is paused, resume it
    if intervention.run_id:
        run = db.query(Run).filter(Run.id == intervention.run_id).first()
        
        if run and run.status == "waiting_for_human":
            resume_run(db, run)
            db.commit()
            
            # Re-queue the run
            from app.celery_app import celery_app
            celery_app.send_task("runs.execute", args=[str(run.id)])
            
            return {
                "success": True,
                "message": "Intervention resolved and run resumed",
                "intervention_id": intervention_id,
                "run_id": str(run.id),
                "run_status": run.status
            }
    
    return {
        "success": True,
        "message": "Intervention resolved",
        "intervention_id": intervention_id
    }
