"""
SSE Event Stream for Real-Time HITL Dashboard

Emits:
- run.started
- run.progress
- intervention.created
- intervention.resolved
- run.completed

Architecture:
- Celery workers emit events via Redis pub/sub
- SSE endpoint subscribes to Redis and broadcasts to connected clients
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
from typing import AsyncGenerator
from datetime import datetime
import redis.asyncio as redis
from app.config import settings

router = APIRouter()


class EventBroadcaster:
    """Thread-safe event broadcaster for SSE"""
    
    def __init__(self):
        self.listeners = set()
    
    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.listeners.add(queue)
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        self.listeners.discard(queue)
    
    async def broadcast(self, event: dict):
        """Broadcast event to all listeners"""
        for queue in self.listeners:
            await queue.put(event)


# Global broadcaster instance
broadcaster = EventBroadcaster()


async def event_generator() -> AsyncGenerator[str, None]:
    """
    Generate SSE events for client.
    
    Subscribes to Redis pub/sub channel and forwards events as SSE.
    """
    # Connect to Redis
    redis_client = redis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to events channel
        await pubsub.subscribe("scraper:events")
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        
        # Listen for events
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message and message['type'] == 'message':
                # Forward event to client
                event_data = message['data'].decode('utf-8')
                yield f"data: {event_data}\n\n"
            
            # Send keepalive every second
            await asyncio.sleep(0.1)
    
    except asyncio.CancelledError:
        await pubsub.unsubscribe("scraper:events")
        await redis_client.close()
        raise
    
    finally:
        await pubsub.close()
        await redis_client.close()


@router.get("/runs/events")
async def run_events():
    """
    SSE endpoint for real-time run and intervention events.
    
    Event types:
    - run.started: { type, run_id, job_id, target_url }
    - run.progress: { type, run_id, stage, engine }
    - intervention.created: { type, intervention_id, reason, priority }
    - intervention.resolved: { type, intervention_id, resolution }
    - run.completed: { type, run_id, status, stats }
    - run.failed: { type, run_id, error_message }
    """
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Event emission helpers (called from workers and services)

async def emit_run_started(run_id: str, job_id: str, target_url: str):
    """Emit run started event"""
    await broadcaster.broadcast({
        "type": "run.started",
        "run_id": run_id,
        "job_id": job_id,
        "target_url": target_url,
        "timestamp": datetime.utcnow().isoformat()
    })


async def emit_run_progress(run_id: str, stage: str, engine: str):
    """Emit run progress event"""
    await broadcaster.broadcast({
        "type": "run.progress",
        "run_id": run_id,
        "stage": stage,
        "engine": engine,
        "timestamp": datetime.utcnow().isoformat()
    })


async def emit_intervention_created(intervention_id: str, intervention_type: str, reason: str, priority: str):
    """Emit intervention created event"""
    await broadcaster.broadcast({
        "type": "intervention.created",
        "intervention_id": intervention_id,
        "intervention_type": intervention_type,
        "reason": reason,
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat()
    })


async def emit_intervention_resolved(intervention_id: str, resolution: dict):
    """Emit intervention resolved event"""
    await broadcaster.broadcast({
        "type": "intervention.resolved",
        "intervention_id": intervention_id,
        "resolution": resolution,
        "timestamp": datetime.utcnow().isoformat()
    })


async def emit_run_completed(run_id: str, status: str, stats: dict):
    """Emit run completed event"""
    await broadcaster.broadcast({
        "type": "run.completed",
        "run_id": run_id,
        "status": status,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    })


async def emit_run_failed(run_id: str, error_message: str, failure_code: str):
    """Emit run failed event"""
    await broadcaster.broadcast({
        "type": "run.failed",
        "run_id": run_id,
        "error_message": error_message,
        "failure_code": failure_code,
        "timestamp": datetime.utcnow().isoformat()
    })
