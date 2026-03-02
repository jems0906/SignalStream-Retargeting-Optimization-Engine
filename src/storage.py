import redis
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .models import UserProfile, AudienceMember, UserEvent, OptimizationSignal, RetargetingEvent
from .config import RedisConfig
from .exceptions import RedisConnectionError, StorageError
import logging


class RedisStorage:
    """Redis-based storage implementation"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        try:
            self.redis_client = redis.Redis(
                host=config.host,
                port=config.port, 
                db=config.db,
                password=config.password if config.password else None,
                socket_timeout=config.socket_timeout,
                socket_connect_timeout=config.socket_connect_timeout,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.logger.info(f"Connected to Redis at {config.host}:{config.port}")
        except redis.RedisError as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise RedisConnectionError(f"Cannot connect to Redis: {e}") from e
    
    # User Profile Operations
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from Redis"""
        try:
            profile_data = self.redis_client.get(f"user:{user_id}")
            if profile_data:
                return UserProfile.model_validate(json.loads(profile_data))
            return None
        except (redis.RedisError, json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Error getting user profile {user_id}: {e}")
            raise StorageError(f"Failed to get user profile: {e}") from e
    
    def save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile to Redis"""
        try:
            profile_key = f"user:{profile.user_id}"
            profile_data = json.loads(profile.model_dump_json())
            self.redis_client.set(profile_key, json.dumps(profile_data))
        except (redis.RedisError, json.JSONEncodeError) as e:
            self.logger.error(f"Error saving user profile {profile.user_id}: {e}")
            raise StorageError(f"Failed to save user profile: {e}") from e
    
    def update_user_last_seen(self, user_id: str, timestamp: datetime) -> None:
        """Update user's last seen timestamp"""
        self.redis_client.hset(f"user:{user_id}:metadata", "last_seen", timestamp.isoformat())
    
    # Audience Operations
    def add_user_to_audience(self, user_id: str, audience_id: str) -> None:
        """Add user to an audience"""
        member = AudienceMember(user_id=user_id, added_at=datetime.now())
        self.redis_client.sadd(f"audience:{audience_id}:members", user_id)
        self.redis_client.set(
            f"audience:{audience_id}:member:{user_id}", 
            member.model_dump_json()
        )
        # Also update user's audience list
        self.redis_client.sadd(f"user:{user_id}:audiences", audience_id)
    
    def remove_user_from_audience(self, user_id: str, audience_id: str) -> None:
        """Remove user from an audience"""
        self.redis_client.srem(f"audience:{audience_id}:members", user_id)
        self.redis_client.delete(f"audience:{audience_id}:member:{user_id}")
        self.redis_client.srem(f"user:{user_id}:audiences", audience_id)
    
    def get_audience_members(self, audience_id: str) -> List[AudienceMember]:
        """Get all members of an audience"""
        members = []
        user_ids = self.redis_client.smembers(f"audience:{audience_id}:members")
        for user_id in user_ids:
            member_data = self.redis_client.get(f"audience:{audience_id}:member:{user_id}")
            if member_data:
                members.append(AudienceMember.model_validate(json.loads(member_data)))
        return members
    
    def get_user_audiences(self, user_id: str) -> List[str]:
        """Get all audiences a user belongs to"""
        return list(self.redis_client.smembers(f"user:{user_id}:audiences"))
    
    # Event Queue Operations
    def enqueue_event(self, event: UserEvent) -> None:
        """Add event to processing queue"""
        self.redis_client.lpush("event_queue", event.model_dump_json())
    
    def dequeue_event(self) -> Optional[UserEvent]:
        """Get next event from processing queue"""
        event_data = self.redis_client.brpop("event_queue", timeout=1)
        if event_data:
            return UserEvent.model_validate(json.loads(event_data[1]))
        return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.redis_client.llen("event_queue")
    
    # Optimization Signals
    def save_optimization_signal(self, signal: OptimizationSignal) -> None:
        """Save optimization signal"""
        signal_key = f"signal:{signal.user_id}:{signal.signal_type}:{signal.timestamp.isoformat()}"
        self.redis_client.set(signal_key, signal.model_dump_json())
        # Also add to user's signal list
        self.redis_client.lpush(f"user:{signal.user_id}:signals", signal_key)
        # Keep only last 100 signals per user
        self.redis_client.ltrim(f"user:{signal.user_id}:signals", 0, 99)
    
    def get_user_recent_events(self, user_id: str, hours: int = 24) -> List[UserEvent]:
        """Get user's recent events within specified hours"""
        events = []
        event_keys = self.redis_client.lrange(f"user:{user_id}:events", 0, -1)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for event_key in event_keys:
            event_data = self.redis_client.get(event_key)
            if event_data:
                event = UserEvent.model_validate(json.loads(event_data))
                if event.timestamp >= cutoff_time:
                    events.append(event)
        return events
    
    def save_user_event(self, user_id: str, event: UserEvent) -> None:
        """Save user event for history tracking"""
        event_key = f"event:{user_id}:{event.timestamp.isoformat()}:{event.event_type}"
        self.redis_client.set(event_key, event.model_dump_json())
        self.redis_client.lpush(f"user:{user_id}:events", event_key)
        # Keep only last 1000 events per user
        self.redis_client.ltrim(f"user:{user_id}:events", 0, 999)
    
    # Retargeting Events
    def save_retargeting_event(self, event: RetargetingEvent) -> None:
        """Save retargeting event"""
        event_key = f"retargeting:{event.user_id}:{event.timestamp.isoformat()}"
        self.redis_client.set(event_key, event.model_dump_json())
        self.redis_client.lpush("retargeting_events", event_key)
    
    # Health Check
    def ping(self) -> bool:
        """Check if Redis is available"""
        try:
            return self.redis_client.ping()
        except redis.RedisError as e:
            self.logger.warning(f"Redis ping failed: {e}")
            return False