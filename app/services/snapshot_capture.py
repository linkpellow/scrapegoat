"""
Page snapshot capture for replay-first HITL

Captures page state during extraction for deterministic replay.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.page_snapshot import PageSnapshot


def capture_snapshot(
    db: Session,
    job_id: str,
    run_id: Optional[str],
    url: str,
    html_content: str,
    engine: str,
    status_code: Optional[int] = None
) -> PageSnapshot:
    """
    Capture a page snapshot for HITL replay.
    
    Args:
        db: Database session
        job_id: Job ID
        run_id: Optional run ID
        url: Page URL
        html_content: HTML content
        engine: Engine used (http, playwright, provider)
        status_code: HTTP status code
    
    Returns:
        Created PageSnapshot
    """
    snapshot = PageSnapshot(
        job_id=job_id,
        run_id=run_id,
        url=url,
        html_content=html_content,
        html_size=len(html_content),
        engine=engine,
        status_code=status_code
    )
    
    db.add(snapshot)
    db.flush()
    
    return snapshot


def get_latest_snapshot(
    db: Session,
    job_id: str,
    run_id: Optional[str] = None
) -> Optional[PageSnapshot]:
    """
    Get the latest page snapshot for a job/run.
    
    Args:
        db: Database session
        job_id: Job ID
        run_id: Optional run ID filter
    
    Returns:
        Latest PageSnapshot or None
    """
    query = db.query(PageSnapshot).filter(PageSnapshot.job_id == job_id)
    
    if run_id:
        query = query.filter(PageSnapshot.run_id == run_id)
    
    return query.order_by(PageSnapshot.captured_at.desc()).first()
