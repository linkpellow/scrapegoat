from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Dict, List, Optional

import httpx
from playwright.sync_api import sync_playwright
from celery import Task

from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.enums import ExecutionStrategy
from app.models.job import Job
from app.models.run import Run
from app.models.record import Record
from app.models.field_map import FieldMap
from app.models.session import SessionVault
from app.services.classifier import classify_exception, classify_http_status
from app.services.orchestrator import (
    start_run,
    complete_run,
    fail_run,
    should_retry,
    next_backoff_seconds,
    escalate_strategy,
)

# Scrapy imports
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from app.scraping.spiders.generic import GenericJobSpider
from app.scraping.playwright_extract import extract_with_playwright
from app.scraping.auto_escalation import AutoEscalationEngine, generate_browser_profile
from app.intelligence.adaptive_engine import (
    get_biased_initial_engine,
    record_run_outcome,
    extract_domain,
)
from app.smartfields import process_field
from app.smartfields.types import ExtractionContext
from app.services.intervention_engine import InterventionEngine
from app.models.intervention import InterventionTask
from app.services.event_emitter import (
    emit_run_started,
    emit_run_progress,
    emit_intervention_created,
    emit_run_completed,
    emit_run_failed,
)
from app.services.block_classifier import BlockClassifier
from app.services.session_manager import SessionManager
from app.models.domain_config import DomainConfig
from app.services.orchestrator import pause_run_for_intervention

logger = logging.getLogger(__name__)


def _db() -> Session:
    return SessionLocal()


def _load_field_map(db: Session, job_id: str, job_fields: List[str]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, FieldMap]]:
    """
    Returns (selector_map, field_map_objects).
    
    selector_map: dict[field_name] = selector_spec (for engines)
    field_map_objects: dict[field_name] = FieldMap object (for SmartFields)
    
    If no mapping exists, provides safe defaults.
    """
    rows: List[FieldMap] = db.query(FieldMap).filter(FieldMap.job_id == job_id).all()
    
    selector_map: Dict[str, Dict[str, Any]] = {}
    field_map_objects: Dict[str, FieldMap] = {}
    
    for r in rows:
        selector_map[r.field_name] = r.selector_spec or {}
        field_map_objects[r.field_name] = r

    # Ensure every requested job field has an entry
    out_selector: Dict[str, Dict[str, Any]] = {}
    out_objects: Dict[str, FieldMap] = {}
    
    for f in job_fields:
        if f in selector_map:
            out_selector[f] = selector_map[f]
            out_objects[f] = field_map_objects[f]
        else:
            # safe default: don't guess extraction aggressively
            if f == "title":
                out_selector[f] = {"css": "h1", "all": False}
            else:
                out_selector[f] = {"css": "", "all": False}
            # Create temporary FieldMap for defaults (no SmartFields processing)
            # These won't be in out_objects, so SmartFields will be skipped for them

    return out_selector, out_objects


def _apply_smartfields(
    records: List[Dict[str, Any]],
    field_map_objects: Dict[str, FieldMap],
    context: ExtractionContext
) -> List[Dict[str, Any]]:
    """
    Apply SmartFields processing to extracted records.
    
    Returns records with SmartField metadata attached:
    {
        "title": "Product Name",
        "_smartfields": {
            "title": {
                "value": "Product Name",
                "raw": "  Product Name  ",
                "confidence": 0.95,
                "reasons": ["normalized_whitespace", "normalized_successfully"],
                "errors": []
            }
        }
    }
    """
    processed_records = []
    
    for record in records:
        processed_record = {}
        smartfields_meta = {}
        
        for field_name, raw_value in record.items():
            # Skip metadata fields
            if field_name.startswith("_"):
                processed_record[field_name] = raw_value
                continue
            
            # Check if SmartFields config exists for this field
            if field_name in field_map_objects:
                fm = field_map_objects[field_name]
                field_type = fm.field_type or "string"
                smart_config = fm.smart_config or {}
                validation_rules = fm.validation_rules or {}
                
                # Process through SmartFields pipeline
                result = process_field(
                    field_name=field_name,
                    raw_value=raw_value,
                    field_type=field_type,
                    smart_config=smart_config,
                    validation_rules=validation_rules,
                    context=context
                )
                
                # Use normalized value
                processed_record[field_name] = result.value
                smartfields_meta[field_name] = result.dict()
            else:
                # No SmartFields config - use raw value
                processed_record[field_name] = raw_value
        
        # Attach SmartFields metadata
        processed_record["_smartfields"] = smartfields_meta
        processed_records.append(processed_record)
    
    return processed_records


def _scrapy_extract(start_url: str, field_map: Dict[str, Any], crawl_mode: str = "single", list_config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """
    Runs Scrapy spider and returns list of items by writing to a temp JSON feed.
    This avoids Twisted reactor lifetime issues inside Celery.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "items.json")

        s = get_project_settings()
        # Make it self-contained even without a scrapy.cfg project.
        custom_settings = {
            "LOG_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "DOWNLOAD_TIMEOUT": settings.http_timeout_seconds,
            "USER_AGENT": "scraper-platform/1.0",
            "FEEDS": {out_path: {"format": "json", "encoding": "utf8", "indent": 2}},
        }

        process = CrawlerProcess(settings={**dict(s), **custom_settings})
        process.crawl(
            GenericJobSpider,
            start_url=start_url,
            field_map=field_map,
            crawl_mode=crawl_mode,
            list_config=list_config or {},
        )
        process.start()  # blocks until done

        if not os.path.exists(out_path):
            return []

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, list) else []


@celery_app.task(bind=True, name="runs.execute", autoretry_for=(), retry_backoff=False)
def execute_run(self: Task, run_id: str) -> None:
    """
    Execute a scraping run with intelligent auto-escalation.
    
    If engine_mode="auto", will escalate HTTP → Playwright → Provider based on signals.
    Logs all attempts to run.engine_attempts for transparency.
    """
    db = _db()
    try:
        run: Run | None = db.query(Run).filter(Run.id == run_id).one_or_none()
        if not run:
            return

        job: Job | None = db.query(Job).filter(Job.id == run.job_id).one_or_none()
        if not job:
            fail_run(db, run, "unknown", "Job not found for run")
            db.commit()
            return

        logger.info(f"Starting run {run_id} for job {run.job_id} - URL: {job.target_url}")
        start_run(db, run)
        db.commit()
        
        # Emit run started event
        emit_run_started(str(run.id), str(job.id), str(job.target_url))

        # Build field-map contract
        field_map, field_map_objects = _load_field_map(db, str(job.id), list(job.fields or []))
        
        # Build extraction context for SmartFields
        from datetime import datetime
        extraction_context = ExtractionContext(
            url=str(job.target_url),
            fetched_at=datetime.now().isoformat(),
            engine="unknown",  # Will be updated per attempt
            locale=getattr(job, 'locale', 'en-US'),
            timezone=getattr(job, 'timezone', 'UTC'),
            country=getattr(job, 'country', 'US')
        )
        
        # PROACTIVE SESSION HEALTH PROBE (before execution)
        # Skip probe for sites that don't require authentication
        logger.info(f"Run {run_id}: Extracting domain from URL")
        session_data = None
        domain = extract_domain(job.target_url)
        logger.info(f"Run {run_id}: Domain={domain}, requires_auth={job.requires_auth}")
        
        if job.requires_auth:
            # Probe session health BEFORE starting execution (only for auth-required sites)
            from app.services.session_probe import SessionProbe
            import asyncio
            
            is_healthy, intervention_id = asyncio.run(
                SessionProbe.probe_before_run(
                    db=db,
                    domain=domain,
                    job_id=str(job.id),
                    run_id=str(run.id)
                )
            )
            
            if not is_healthy:
                # Session probe failed - intervention already created
                emit_intervention_created(
                    intervention_id,
                    "login_refresh",
                    "Session invalid (proactive probe)",
                    "normal"
                )
                
                pause_run_for_intervention(db, run, "Session invalid", intervention_id)
                db.commit()
                return
            
            # Load session if available (already validated by probe)
            session_vault = SessionManager.get_valid_session(db, domain)
            if session_vault:
                session_data = session_vault.session_data

        # PROVIDER ROUTING: Check if we should skip direct attempts
        logger.info(f"Run {run_id}: Calling ProviderRouter.should_skip_direct_attempts")
        from app.services.provider_router import ProviderRouter
        
        should_skip = ProviderRouter.should_skip_direct_attempts(
            db=db,
            domain=domain,
            has_session=(session_data is not None)
        )
        logger.info(f"Run {run_id}: should_skip={should_skip}")
        
        if should_skip:
            # Domain requires provider - skip escalation
            initial_strategy = ExecutionStrategy.API_REPLAY
            engine_mode = "provider"
            bias_reason = "Domain classified as INFRA or high-block HUMAN - routing to provider"
        else:
            # Use intelligent routing
            initial_strategy, bias_reason = ProviderRouter.get_initial_strategy(
                db=db,
                domain=domain,
                has_session=(session_data is not None)
            )
            engine_mode = getattr(job, 'engine_mode', 'auto')
        
        # Initialize auto-escalation engine
        logger.info(f"Run {run_id}: Initializing AutoEscalationEngine with mode={engine_mode}")
        escalation = AutoEscalationEngine(engine_mode=engine_mode)
        logger.info(f"Run {run_id}: AutoEscalationEngine initialized")
        
        # Get browser profile (generate if not exists)
        browser_profile = getattr(job, 'browser_profile', None) or {}
        if not browser_profile:
            browser_profile = generate_browser_profile()
            job.browser_profile = browser_profile
            db.commit()

        # Determine initial engine (already set by provider routing if needed)
        if initial_strategy == ExecutionStrategy.API_REPLAY:
            current_engine = "provider"
        else:
            # ADAPTIVE INTELLIGENCE: Get biased initial engine based on domain history
            current_engine, adaptive_bias = get_biased_initial_engine(
                db=db,
                url=job.target_url,
                engine_mode=engine_mode
            )
            if adaptive_bias:
                bias_reason = adaptive_bias
        
        # Log bias decision if applied
        if bias_reason:
            escalation.log_attempt(
                engine="adaptive_intelligence",
                status=0,
                signals=[bias_reason],
                decision="initial_engine_biased",
                success=False
            )
        
        # Auto-escalation loop
        max_escalations = 3
        escalation_count = 0
        
        logger.info(f"Run {run_id}: Starting escalation loop with engine={current_engine}, mode={engine_mode}")
        
        while escalation_count < max_escalations:
            try:
                logger.info(f"Run {run_id}: Executing with engine={current_engine}, attempt={escalation_count+1}/{max_escalations}")
                # Execute with current engine
                items, html, status_code = _execute_with_engine(
                    engine=current_engine,
                    job=job,
                    field_map=field_map,
                    session_data=session_data,
                    browser_profile=browser_profile
                )
                logger.info(f"Run {run_id}: Engine {current_engine} returned {len(items) if items else 0} items, status={status_code}")
                
                # Check if we got results
                if items:
                    # Success! Log attempt
                    escalation.log_attempt(
                        engine=current_engine,
                        status=status_code,
                        signals=[],
                        decision="success",
                        success=True
                    )
                    
                    # Apply SmartFields processing
                    extraction_context.engine = current_engine
                    extraction_context.fetched_at = datetime.now().isoformat()
                    items = _apply_smartfields(items, field_map_objects, extraction_context)
                    
                    # HITL: Check for low-confidence fields that need intervention
                    for it in items:
                        smartfields_meta = it.get("_smartfields", {})
                        for field_name, field_result in smartfields_meta.items():
                            # Check if this field is required
                            is_required = False
                            if field_name in field_map_objects:
                                validation_rules = field_map_objects[field_name].validation_rules or {}
                                is_required = validation_rules.get("required", False)
                            
                            # Check for low confidence intervention
                            intervention_spec = InterventionEngine.should_intervene_field_confidence(
                                field_name=field_name,
                                field_result=field_result,
                                is_required=is_required
                            )
                            
                            if intervention_spec:
                                # Create intervention task
                                task = InterventionEngine.create_intervention(
                                    db=db,
                                    job_id=str(job.id),
                                    run_id=str(run.id),
                                    intervention_spec=intervention_spec
                                )
                                # Emit intervention created event
                                emit_intervention_created(
                                    str(task.id),
                                    task.type,
                                    task.trigger_reason,
                                    task.priority
                                )
                                # Only create one intervention per run to avoid spam
                                break
                    
                    # Persist records
                    inserted = 0
                    for it in items:
                        db.add(Record(run_id=run.id, data=it))
                        inserted += 1
                    
                    # Store attempt log
                    run.engine_attempts = escalation.get_attempts_log()
                    db.commit()
                    
                    stats = {
                        "records_inserted": inserted,
                        "engine_used": current_engine,
                        "escalations": escalation_count,
                        "target_url": job.target_url,
                        "crawl_mode": job.crawl_mode,
                        "domain": extract_domain(job.target_url),
                        "bias_reason": bias_reason,
                    }
                    complete_run(db, run, stats)
                    
                    # ADAPTIVE INTELLIGENCE: Record successful outcome
                    record_run_outcome(
                        db=db,
                        url=job.target_url,
                        engine=current_engine,
                        success=True,
                        records_extracted=inserted,
                        escalations=escalation_count
                    )
                    
                    db.commit()
                    return
                
                # No items extracted - check if we should escalate
                decision = None
                if current_engine == "http":
                    decision = escalation.should_escalate_from_http(
                        html=html,
                        status_code=status_code,
                        extracted_count=0,
                        required_selectors=len(field_map)
                    )
                elif current_engine == "playwright":
                    decision = escalation.should_escalate_from_playwright(
                        html=html,
                        status_code=status_code
                    )
                
                if decision and escalation.can_escalate(current_engine):
                    # Escalate to next tier
                    escalation.log_attempt(
                        engine=current_engine,
                        status=status_code,
                        signals=decision.signals,
                        decision=f"escalate:{decision.reason}",
                        success=False
                    )
                    current_engine = decision.to_engine
                    escalation_count += 1
                else:
                    # No escalation possible or needed - fail
                    escalation.log_attempt(
                        engine=current_engine,
                        status=status_code,
                        signals=["no_items_extracted"],
                        decision="failed",
                        success=False
                    )
                    run.engine_attempts = escalation.get_attempts_log()
                    
                    # ADAPTIVE INTELLIGENCE: Record failed outcome
                    record_run_outcome(
                        db=db,
                        url=job.target_url,
                        engine=current_engine,
                        success=False,
                        records_extracted=0,
                        escalations=escalation_count
                    )
                    
                    db.commit()
                    
                    # NEW LOGIC: Determine if should pause or fail
                    domain = extract_domain(job.target_url)
                    
                    # Get domain config for access class
                    domain_config = db.query(DomainConfig).filter(
                        DomainConfig.domain == domain
                    ).first()
                    access_class = domain_config.access_class if domain_config else "public"
                    
                    # Classify block
                    should_pause, intervention_type, intervention_reason = BlockClassifier.should_pause_for_intervention(
                        response_code=status_code,
                        error_message=f"No items extracted with {current_engine}",
                        has_session=(session_data is not None),
                        domain_access_class=access_class
                    )
                    
                    if should_pause:
                        # PAUSE run and create intervention
                        block_rate = domain_config.block_rate_403 if domain_config else 0.0
                        priority = BlockClassifier.get_intervention_priority(intervention_type, block_rate)
                        
                        task = InterventionEngine.create_intervention(
                            db=db,
                            job_id=str(job.id),
                            run_id=str(run.id),
                            intervention_spec={
                                "type": intervention_type,
                                "reason": intervention_reason,
                                "priority": priority,
                                "payload": {
                                    "url": str(job.target_url),
                                    "domain": domain,
                                    "status_code": status_code,
                                    "engine_used": current_engine,
                                    "escalation_count": escalation_count
                                }
                            }
                        )
                        db.commit()
                        
                        # Emit intervention created event
                        emit_intervention_created(
                            str(task.id),
                            task.type,
                            task.trigger_reason,
                            task.priority
                        )
                        
                        # PAUSE (not fail)
                        pause_run_for_intervention(db, run, intervention_reason, str(task.id))
                        db.commit()
                        
                        # Update domain stats
                        SessionManager.update_domain_stats(
                            db=db,
                            domain=domain,
                            success=False,
                            engine=current_engine,
                            response_code=status_code,
                            had_session=(session_data is not None)
                        )
                        
                        return  # Exit, waiting for human
                    else:
                        # Traditional FAIL
                        fail_run(db, run, "extraction_failed", f"No items extracted with {current_engine}")
                        db.commit()
                        
                        # Update domain stats
                        SessionManager.update_domain_stats(
                            db=db,
                            domain=domain,
                            success=False,
                            engine=current_engine,
                            response_code=status_code,
                            had_session=(session_data is not None)
                        )
                        
                        return
                    
            except Exception as e:
                # Log failed attempt
                escalation.log_attempt(
                    engine=current_engine,
                    status=0,
                    signals=[str(type(e).__name__)],
                    decision="error",
                    success=False
                )
                
                # Check if we can escalate on error
                if escalation.can_escalate(current_engine):
                    # Try next tier
                    tier_idx = escalation.TIER_ORDER.index(current_engine)
                    current_engine = escalation.TIER_ORDER[tier_idx + 1]
                    escalation_count += 1
                else:
                    # No more escalation - fail
                    run.engine_attempts = escalation.get_attempts_log()
                    db.commit()
                    
                    failure = classify_exception(e)
                    
                    # HITL: Check for auth expired intervention
                    auth_spec = InterventionEngine.should_intervene_auth_expired(
                        failure_code=failure.code.value,
                        job=job,
                        run=run
                    )
                    if auth_spec:
                        task = InterventionEngine.create_intervention(
                            db=db,
                            job_id=str(job.id),
                            run_id=str(run.id),
                            intervention_spec=auth_spec
                        )
                        db.commit()
                        # Emit intervention created event
                        emit_intervention_created(
                            str(task.id),
                            task.type,
                            task.trigger_reason,
                            task.priority
                        )
                    
                    fail_run(db, run, failure.code.value, failure.message)
                    db.commit()
                    return
        
        # Max escalations reached
        run.engine_attempts = escalation.get_attempts_log()
        db.commit()
        fail_run(db, run, "max_escalations", "Reached maximum escalation attempts")
        db.commit()

    except Exception as e:
        # Top-level error
        try:
            failure = classify_exception(e)
            fail_run(db, run, failure.code.value, failure.message)
            db.commit()
        except:
            pass
    finally:
        db.close()


def _execute_with_engine(
    engine: str,
    job: Job,
    field_map: Dict[str, Any],
    session_data: Optional[Dict[str, Any]],
    browser_profile: Dict[str, Any]
) -> tuple[List[Dict[str, Any]], str, int]:
    """
    Execute extraction with specified engine.
    
    Returns: (items, html, status_code)
    """
    if engine == "http":
        # HTTP via Scrapy
        items = _scrapy_extract(
            job.target_url,
            field_map,
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {},
        )
        # For Scrapy, we don't have easy access to raw HTML, so return empty string
        return items, "", 200
    
    elif engine == "playwright":
        # Browser via Playwright with stable profile
        items = _extract_with_playwright_stable(
            url=job.target_url,
            field_map=field_map,
            session_data=session_data,
            browser_profile=browser_profile,
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {}
        )
        return items, "", 200
    
    elif engine == "provider":
        # Provider (ScrapingBee) - handles JS rendering and anti-bot bypassing
        items = _extract_with_scrapingbee(
            url=job.target_url,
            field_map=field_map,
            crawl_mode=job.crawl_mode,
            list_config=job.list_config or {}
        )
        return items, "", 200
    
    else:
        raise ValueError(f"Unknown engine: {engine}")


def _extract_with_playwright_stable(
    url: str,
    field_map: Dict[str, Any],
    session_data: Optional[Dict[str, Any]],
    browser_profile: Dict[str, Any],
    crawl_mode: str = "single",
    list_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Enhanced Playwright extraction with stable browser fingerprint.
    """
    if crawl_mode == "list":
        # List mode with Playwright not yet fully implemented
        # Fall back to Scrapy for now
        return _scrapy_extract(url, field_map, crawl_mode, list_config or {})
    else:
        return extract_with_playwright(url, field_map, session_data, browser_profile)


def _extract_with_scrapingbee(
    url: str,
    field_map: Dict[str, Any],
    crawl_mode: str = "single",
    list_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Extract data using ScrapingBee API for JS rendering and anti-bot bypassing.
    
    Supports both single-page and list crawling modes.
    """
    from app.config import settings
    from app.scraping.extraction import extract_from_html_css
    from urllib.parse import urljoin
    
    logger.info(f"ScrapingBee: Starting extraction for {url}, mode={crawl_mode}")
    
    if not settings.scrapingbee_api_key:
        logger.error("ScrapingBee API key not configured!")
        raise ValueError("ScrapingBee API key not configured")
    
    logger.info(f"ScrapingBee: API key configured (length={len(settings.scrapingbee_api_key)})")
    scrapingbee_url = "https://app.scrapingbee.com/api/v1/"
    
    def _extract_fields(html: str) -> Dict[str, Any]:
        """Extract all fields from HTML using field_map"""
        item = {}
        for field_name, spec in field_map.items():
            value = extract_from_html_css(html, spec)
            if value is not None:
                item[field_name] = value
        return item
    
    if crawl_mode == "list":
        # List mode: extract list items and optionally paginate
        all_items = []
        visited_urls = set()
        current_url = url
        page_count = 0
        max_pages = 10  # Safety limit
        
        while current_url and page_count < max_pages:
            if current_url in visited_urls:
                break
            
            visited_urls.add(current_url)
            page_count += 1
            
            # Fetch page via ScrapingBee
            params = {
                'api_key': settings.scrapingbee_api_key,
                'url': current_url,
                'render_js': 'true',
                'premium_proxy': 'false',
                'country_code': 'us'
            }
            
            try:
                response = httpx.get(scrapingbee_url, params=params, timeout=60.0)
                response.raise_for_status()
                html = response.text
            except Exception as e:
                logger.error(f"ScrapingBee request failed for {current_url}: {e}")
                break
            
            # For list mode, extract multiple items from the page
            # First check if we have item_links to follow
            if list_config and list_config.get("item_links"):
                # Extract list of item URLs
                item_links_spec = list_config["item_links"]
                item_urls = extract_from_html_css(html, item_links_spec)
                
                if not isinstance(item_urls, list):
                    item_urls = [item_urls] if item_urls else []
                
                # Fetch and extract each item (limit to avoid too many requests)
                for item_url in item_urls[:20]:  # Limit to 20 items per page
                    full_item_url = urljoin(current_url, item_url)
                    
                    # Fetch item detail page
                    item_params = {
                        'api_key': settings.scrapingbee_api_key,
                        'url': full_item_url,
                        'render_js': 'true',
                        'premium_proxy': 'false',
                        'country_code': 'us'
                    }
                    
                    try:
                        item_response = httpx.get(scrapingbee_url, params=item_params, timeout=60.0)
                        item_response.raise_for_status()
                        item_html = item_response.text
                        
                        # Extract fields from item page
                        item = _extract_fields(item_html)
                        if item:
                            item['_url'] = full_item_url
                            all_items.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to fetch item {full_item_url}: {e}")
                        continue
            else:
                # No item links - extract fields directly from list page
                item = _extract_fields(html)
                if item:
                    item['_url'] = current_url
                    all_items.append(item)
            
            # Find next page link if pagination configured
            if list_config and list_config.get("pagination"):
                pagination_spec = list_config["pagination"]
                next_href = extract_from_html_css(html, pagination_spec)
                
                if next_href:
                    current_url = urljoin(current_url, next_href)
                else:
                    current_url = None
            else:
                current_url = None
        
        return all_items
    
    else:
        # Single page mode
        params = {
            'api_key': settings.scrapingbee_api_key,
            'url': url,
            'render_js': 'true',
            'premium_proxy': 'false',
            'country_code': 'us'
        }
        
        try:
            response = httpx.get(scrapingbee_url, params=params, timeout=60.0)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"ScrapingBee request failed: {e}")
            raise
        
        item = _extract_fields(html)
        return [item] if item else []
