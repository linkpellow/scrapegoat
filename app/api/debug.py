"""
Debug endpoints for troubleshooting.
"""
from fastapi import APIRouter
from sqlalchemy import desc
from app.database import SessionLocal
from app.models.run import Run
from typing import List, Dict, Any

router = APIRouter()


@router.get("/debug/failed-runs")
def get_failed_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent failed runs with error details."""
    db = SessionLocal()
    try:
        runs = db.query(Run).filter(Run.status == "failed").order_by(desc(Run.updated_at)).limit(limit).all()
        
        result = []
        for run in runs:
            result.append({
                "run_id": str(run.id),
                "job_id": str(run.job_id),
                "status": run.status,
                "failure_code": run.failure_code,
                "error_message": run.error_message,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None,
                "engine_attempts": run.engine_attempts
            })
        
        return result
    finally:
        db.close()
