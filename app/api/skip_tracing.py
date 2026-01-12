"""
Skip Tracing API Adapter

Wraps the scraper platform to provide skip tracing functionality
matching the existing API format.

Supports:
1. Search by name
2. Search by name + address
3. Search by email
4. Search by phone
5. Details by Person ID

Uses FastPeopleSearch and TruePeopleSearch (free sites, no auth required).
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.job import Job
from app.models.run import Run
from app.models.record import Record
from app.services.orchestrator import create_run
from app.services.people_search_adapter import PeopleSearchAdapter
from app.celery_app import celery_app
import time
import uuid
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def _db() -> Session:
    return SessionLocal()


# Configuration: Site priority (try in order)
SITE_PRIORITY = ["fastpeoplesearch", "truepeoplesearch"]


# Request/Response Models

class PersonDetails(BaseModel):
    """Person details in skip tracing format"""
    person_id: str = Field(alias="Person ID")
    telephone: str = Field(alias="Telephone")
    age: Optional[int] = Field(None, alias="Age")
    
    # Location (optional)
    address_region: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    
    # Alternative field names
    phone: Optional[str] = None
    phone_number: Optional[str] = None
    
    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class SkipTracingResponse(BaseModel):
    """Primary skip tracing response format"""
    success: bool
    data: Dict[str, Any]


class PhoneDetail(BaseModel):
    """Detailed phone information"""
    phone_number: str
    phone_type: str  # "Wireless" | "Landline" | "VoIP"
    last_reported: Optional[str] = None


class PersonDetailedResponse(BaseModel):
    """Detailed person lookup response"""
    success: bool
    data: Dict[str, Any]


# Helper Functions

def _create_scraper_job(
    site_name: str,
    search_type: str,
    search_params: Dict[str, str]
) -> str:
    """
    Create a scraper job using PeopleSearchAdapter.
    
    Args:
        site_name: "fastpeoplesearch" or "truepeoplesearch"
        search_type: "search_by_name" | "search_by_phone" | "person_details"
        search_params: Search parameters (name, phone, location, etc.)
    
    Returns:
        job_id (str)
    """
    db = _db()
    try:
        job_id = PeopleSearchAdapter.create_search_job(
            db=db,
            site_name=site_name,
            search_type=search_type,
            search_params=search_params
        )
        return job_id
    finally:
        db.close()


def _execute_and_wait(job_id: str, site_name: str, timeout: int = 60) -> tuple[List[Dict[str, Any]], str]:
    """
    Execute scraper job and wait for results.
    
    Returns:
        (records, site_used)
    """
    db = _db()
    try:
        # Get job to determine strategy
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return [], site_name
        
        # Create run with resolved strategy
        from app.enums import ExecutionStrategy
        resolved = ExecutionStrategy(job.strategy)
        run = create_run(db, job, resolved)
        db.commit()
        
        # Execute async
        celery_app.send_task("runs.execute", args=[str(run.id)])
        
        # Poll for completion
        start_time = time.time()
        while time.time() - start_time < timeout:
            db.refresh(run)
            
            if run.status == "completed":
                # Get records
                records = db.query(Record).filter(Record.run_id == run.id).all()
                return [r.data for r in records], site_name
            
            elif run.status == "failed":
                logger.warning(f"Scraper failed for {site_name}: {run.error_message}")
                return [], site_name  # Return empty, caller will try next site
            
            time.sleep(1)
        
        logger.warning(f"Scraper timeout for {site_name}")
        return [], site_name  # Return empty on timeout
    
    finally:
        db.close()


def _execute_with_fallback(
    search_type: str,
    search_params: Dict[str, str],
    timeout: int = 60
) -> tuple[List[Dict[str, Any]], str]:
    """
    Execute search with fallback across multiple sites.
    
    Tries sites in SITE_PRIORITY order until one succeeds.
    
    Returns:
        (records, site_used)
    """
    for site_name in SITE_PRIORITY:
        try:
            logger.info(f"Trying {site_name} for {search_type}")
            
            # Create job
            job_id = _create_scraper_job(site_name, search_type, search_params)
            
            # Execute and wait
            records, _ = _execute_and_wait(job_id, site_name, timeout)
            
            if records:
                logger.info(f"Success with {site_name}: {len(records)} records")
                return records, site_name
            
            logger.info(f"No results from {site_name}, trying next site")
        
        except Exception as e:
            logger.error(f"Error with {site_name}: {e}")
            continue
    
    # All sites failed
    raise HTTPException(
        status_code=404,
        detail="No results found from any people search site"
    )


def _map_to_person_details(records: List[Dict[str, Any]]) -> List[PersonDetails]:
    """
    Map scraper records to PersonDetails format.
    
    Handles field name variations and generates Person IDs.
    """
    people = []
    
    for record in records:
        # Extract phone (try multiple field names)
        telephone = (
            record.get("phone") or
            record.get("phone_number") or
            record.get("telephone") or
            ""
        )
        
        # Extract age
        age = record.get("age")
        if age and isinstance(age, str):
            try:
                age = int(age)
            except ValueError:
                age = None
        
        # Generate Person ID (use phone as base or generate UUID)
        person_id = record.get("person_id") or f"peo_{telephone.replace('+', '').replace('-', '')}"
        
        person = PersonDetails(
            **{
                "Person ID": person_id,
                "Telephone": telephone,
                "Age": age,
                "address_region": record.get("state") or record.get("address_region"),
                "postal_code": record.get("zip_code") or record.get("postal_code"),
                "city": record.get("city"),
                "phone": telephone,
                "phone_number": telephone
            }
        )
        
        people.append(person)
    
    return people


# API Endpoints

@router.post("/search/by-name", response_model=SkipTracingResponse)
def search_by_name(
    name: str = Query(..., description="Full name to search"),
    page: int = Query(1, ge=1, description="Page number")
):
    """
    Search by name.
    
    Priority: HIGH - Most common search method.
    
    Uses FastPeopleSearch (primary) with TruePeopleSearch fallback.
    
    Example: name="John Smith", page=1
    """
    # Execute with fallback
    records, site_used = _execute_with_fallback(
        search_type="search_by_name",
        search_params={"name": name, "page": str(page)},
        timeout=60
    )
    
    # Parse results
    parsed = PeopleSearchAdapter.parse_search_results(records, site_used)
    
    # Map to response format
    people = _map_to_person_details(parsed)
    
    return SkipTracingResponse(
        success=True,
        data={
            "PeopleDetails": [p.dict(by_alias=True) for p in people],
            "Status": 200,
            "_source": site_used  # Track which site was used
        }
    )


@router.post("/search/by-name-address", response_model=SkipTracingResponse)
def search_by_name_and_address(
    name: str = Query(..., description="Full name"),
    citystatezip: str = Query(..., description="City, State ZIP (e.g., 'Denver, CO 80201')")
):
    """
    Search by name + address.
    
    Priority: HIGH - Improves accuracy significantly.
    
    Example: name="John Smith", citystatezip="Denver, CO 80201"
    """
    # Execute with fallback
    records, site_used = _execute_with_fallback(
        search_type="search_by_name",
        search_params={"name": name, "location": citystatezip},
        timeout=60
    )
    
    # Parse results
    parsed = PeopleSearchAdapter.parse_search_results(records, site_used)
    
    # Map to response format
    people = _map_to_person_details(parsed)
    
    return SkipTracingResponse(
        success=True,
        data={
            "PeopleDetails": [p.dict(by_alias=True) for p in people],
            "Status": 200,
            "_source": site_used
        }
    )


@router.post("/search/by-email", response_model=SkipTracingResponse)
def search_by_email(
    email: str = Query(..., description="Email address"),
    phone: Optional[str] = Query(None, description="Optional phone for cross-reference")
):
    """
    Search by email.
    
    Priority: MEDIUM - For enriching leads with email data.
    
    Note: Email search may not be supported by all sites.
    Falls back to name search if email-specific search fails.
    
    Example: email="john@example.com"
    """
    try:
        # Try email-specific search first
        records, site_used = _execute_with_fallback(
            search_type="search_by_email",
            search_params={"email": email},
            timeout=60
        )
    except HTTPException:
        # Email search not widely supported, return empty
        return SkipTracingResponse(
            success=True,
            data={
                "PeopleDetails": [],
                "Status": 200,
                "_source": "none",
                "_note": "Email search not supported by available sites"
            }
        )
    
    # Parse results
    parsed = PeopleSearchAdapter.parse_search_results(records, site_used)
    
    # Map to response format
    people = _map_to_person_details(parsed)
    
    return SkipTracingResponse(
        success=True,
        data={
            "PeopleDetails": [p.dict(by_alias=True) for p in people],
            "Status": 200,
            "_source": site_used
        }
    )


@router.post("/search/by-phone", response_model=SkipTracingResponse)
def search_by_phone(
    phone: str = Query(..., description="Phone number")
):
    """
    Search by phone (reverse lookup).
    
    Priority: MEDIUM - For reverse phone lookup.
    
    Example: phone="+1-303-555-0100"
    """
    # Execute with fallback
    records, site_used = _execute_with_fallback(
        search_type="search_by_phone",
        search_params={"phone": phone},
        timeout=60
    )
    
    # Parse results
    parsed = PeopleSearchAdapter.parse_search_results(records, site_used)
    
    # Map to response format
    people = _map_to_person_details(parsed)
    
    return SkipTracingResponse(
        success=True,
        data={
            "PeopleDetails": [p.dict(by_alias=True) for p in people],
            "Status": 200,
            "_source": site_used
        }
    )


@router.get("/details/{peo_id}", response_model=PersonDetailedResponse)
def get_person_details(peo_id: str):
    """
    Get detailed person information by Person ID.
    
    Priority: HIGH - Critical for two-step enrichment process.
    
    Returns:
    - All phone details (with types: Wireless/Landline/VoIP)
    - Person details
    - Current address details
    - Email addresses
    
    Example: peo_id="peo_13035550100" or person URL from search
    """
    # Execute with fallback
    # peo_id can be either a generated ID or a person URL path
    records, site_used = _execute_with_fallback(
        search_type="person_details",
        search_params={"person_url": peo_id if peo_id.startswith("/") else f"/{peo_id}"},
        timeout=60
    )
    
    if not records:
        raise HTTPException(status_code=404, detail="Person not found")
    
    record = records[0]  # Detail page returns single record
    
    # Parse detailed results
    details = PeopleSearchAdapter.parse_person_details(record, site_used)
    
    # Build response
    return PersonDetailedResponse(
        success=True,
        data={
            "All Phone Details": details["all_phone_details"],
            "Person Details": [details["person_details"]],
            "Current Address Details List": details["address_details"],
            "Email Addresses": details["emails"],
            "_source": site_used
        }
    )


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "skip_tracing_adapter"}
