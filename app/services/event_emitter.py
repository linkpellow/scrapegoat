"""
Synchronous event emitter for Celery workers.

Since Celery workers run synchronously, we need a way to emit
events to the async SSE broadcaster. This uses Redis pub/sub
as a bridge.
"""

import redis
import json
from app.config import settings
from datetime import datetime

# Redis client for pub/sub
redis_client = redis.from_url(settings.redis_url)


def emit_run_started(run_id: str, job_id: str, target_url: str):
    """Emit run started event (sync)"""
    event = {
        "type": "run.started",
        "run_id": run_id,
        "job_id": job_id,
        "target_url": target_url,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))


def emit_run_progress(run_id: str, stage: str, engine: str):
    """Emit run progress event (sync)"""
    event = {
        "type": "run.progress",
        "run_id": run_id,
        "stage": stage,
        "engine": engine,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))


def emit_intervention_created(intervention_id: str, intervention_type: str, reason: str, priority: str):
    """Emit intervention created event (sync)"""
    event = {
        "type": "intervention.created",
        "intervention_id": intervention_id,
        "intervention_type": intervention_type,
        "reason": reason,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))


def emit_intervention_resolved(intervention_id: str, resolution: dict):
    """Emit intervention resolved event (sync)"""
    event = {
        "type": "intervention.resolved",
        "intervention_id": intervention_id,
        "resolution": resolution,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))


def emit_run_completed(run_id: str, status: str, stats: dict):
    """Emit run completed event (sync)"""
    event = {
        "type": "run.completed",
        "run_id": run_id,
        "status": status,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))


def emit_run_failed(run_id: str, error_message: str, failure_code: str):
    """Emit run failed event (sync)"""
    event = {
        "type": "run.failed",
        "run_id": run_id,
        "error_message": error_message,
        "failure_code": failure_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("scraper:events", json.dumps(event))
