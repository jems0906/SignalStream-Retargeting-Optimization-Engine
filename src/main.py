from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .models import UserEvent, UserProfile, AudienceMember, EventType
from .storage import RedisStorage
from .memory_storage import MemoryStorage
from .event_processor import EventProcessor
from .event_generator import EventGenerator
from .config import config
from .exceptions import (
    RedisConnectionError, 
    StorageError, 
    ProcessingError,
    UserProfileNotFoundError,
    InvalidEventError
)


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=config.service_name,
    description=config.description,
    version=config.version
)

# Initialize storage and processor - try Redis first, fallback to memory
try:
    storage = RedisStorage(config.redis)
    logger.info("Using Redis storage")
    storage_type = "Redis"
except RedisConnectionError as e:
    logger.warning(f"Redis not available ({e}), using in-memory storage")
    storage = MemoryStorage(config.processing)
    storage_type = "Memory"

processor = EventProcessor(storage, config.processing)
event_generator = EventGenerator(storage, config.processing)


@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info(f"Starting {config.service_name} v{config.version}")
    logger.info(f"Using {storage_type} storage")
    logger.info("Service started successfully")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": config.service_name,
        "version": config.version,
        "status": "running",
        "storage_type": storage_type,
        "timestamp": datetime.now().isoformat(),
        "storage_connected": storage.ping(),
        "queue_size": storage.get_queue_size()
    }


# Event ingestion endpoints
@app.post("/v1/events")
async def ingest_event(event: UserEvent):
    """Ingest a user event for processing"""
    try:
        # Validate event
        if not event.user_id.strip():
            raise InvalidEventError("User ID cannot be empty")
        
        # Add to processing queue
        storage.enqueue_event(event)
        
        # Process immediately for demo purposes
        # In production, this would be handled by the background worker
        processor.process_event(event)
        
        return {
            "status": "success",
            "message": "Event ingested and processed",
            "event_id": f"{event.user_id}_{event.timestamp.isoformat()}_{event.event_type}"
        }
    except ProcessingError as e:
        logger.error(f"Processing error for event: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    except InvalidEventError as e:
        logger.warning(f"Invalid event: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error ingesting event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/v1/events/batch")
async def ingest_events_batch(events: List[UserEvent]):
    """Ingest multiple events at once"""
    try:
        processed = 0
        for event in events:
            storage.enqueue_event(event)
            processor.process_event(event)
            processed += 1
        
        return {
            "status": "success",
            "message": f"Batch of {processed} events processed",
            "processed_count": processed
        }
    except Exception as e:
        logger.error(f"Error processing event batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Audience endpoints
@app.get("/v1/audiences/{audience_id}/members")
async def get_audience_members(audience_id: str) -> List[AudienceMember]:
    """Get current members for a given audience"""
    try:
        members = storage.get_audience_members(audience_id)
        return members
    except Exception as e:
        logger.error(f"Error fetching audience members: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/audiences")
async def list_audiences():
    """List all available audiences with their definitions"""
    audience_definitions = {
        "cart_abandoners": {
            "name": "Cart Abandoners 24h",
            "description": "Users who added to cart but no purchase in 24h"
        },
        "video_non_converters": {
            "name": "Video Watchers Non-Converters", 
            "description": "Users who watched 75% of video but did not sign up"
        },
        "high_intent": {
            "name": "High Intent Users",
            "description": "Users with high intent score (>0.7)"
        }
    }
    
    # Add member counts
    for audience_id in audience_definitions:
        try:
            members = storage.get_audience_members(audience_id)
            audience_definitions[audience_id]["member_count"] = len(members)
        except StorageError as e:
            logger.warning(f"Error getting audience {audience_id} members: {e}")
            audience_definitions[audience_id]["member_count"] = 0
    
    return audience_definitions


@app.delete("/v1/audiences/{audience_id}/members/{user_id}")
async def remove_user_from_audience(audience_id: str, user_id: str):
    """Remove a user from an audience"""
    try:
        storage.remove_user_from_audience(user_id, audience_id)
        return {
            "status": "success",
            "message": f"User {user_id} removed from audience {audience_id}"
        }
    except Exception as e:
        logger.error(f"Error removing user from audience: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User profile endpoints
@app.get("/v1/users/{user_id}/profile")
async def get_user_profile(user_id: str) -> UserProfile:
    """Show latest user features/scores"""
    try:
        if not user_id.strip():
            raise HTTPException(status_code=400, detail="User ID cannot be empty")
            
        profile = storage.get_user_profile(user_id)
        if not profile:
            raise UserProfileNotFoundError(f"User profile not found: {user_id}")
        
        # Update audiences list from storage
        profile.audiences = storage.get_user_audiences(user_id)
        
        return profile
    except UserProfileNotFoundError:
        raise HTTPException(status_code=404, detail="User profile not found")
    except StorageError as e:
        logger.error(f"Storage error fetching user profile {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error fetching user profile {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/v1/users/{user_id}/events")
async def get_user_events(user_id: str, hours: int = 24):
    """Get user's recent events"""
    try:
        events = storage.get_user_recent_events(user_id, hours)
        return {
            "user_id": user_id,
            "timeframe_hours": hours,
            "event_count": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"Error fetching user events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/users/{user_id}/audiences")
async def get_user_audiences(user_id: str):
    """Get all audiences a user belongs to"""
    try:
        audiences = storage.get_user_audiences(user_id)
        return {
            "user_id": user_id,
            "audiences": audiences,
            "audience_count": len(audiences)
        }
    except Exception as e:
        logger.error(f"Error fetching user audiences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Demo and testing endpoints
@app.post("/v1/demo/generate-events")
async def generate_demo_events(
    count: int = 100,
    background_tasks: BackgroundTasks = None
):
    """Generate demo events for testing"""
    try:
        events = event_generator.generate_batch_events(count)
        
        return {
            "status": "success",
            "message": f"Generated {len(events)} demo events",
            "events_generated": len(events),
            "queue_size": storage.get_queue_size()
        }
    except Exception as e:
        logger.error(f"Error generating demo events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/demo/user-journey")
async def simulate_user_journey(user_id: Optional[str] = None):
    """Simulate a complete user journey"""
    try:
        events = event_generator.simulate_user_journey(user_id)
        
        return {
            "status": "success",
            "message": "User journey simulated",
            "user_id": events[0].user_id if events else None,
            "events_count": len(events),
            "events": events
        }
    except Exception as e:
        logger.error(f"Error simulating user journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/stats")
async def get_service_stats():
    """Get service statistics"""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "queue_size": storage.get_queue_size(),
            "redis_connected": storage.ping()
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Webhook simulation endpoint (optional)
@app.post("/v1/webhooks/ad-platform")
async def ad_platform_webhook(payload: Dict[str, Any]):
    """Simulated webhook endpoint for ad platform integration"""
    try:
        logger.info(f"Received webhook payload: {payload}")
        
        # In a real implementation, this would integrate with
        # actual ad platforms like Facebook, Google Ads, etc.
        
        return {
            "status": "success",
            "message": "Webhook received",
            "processed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))