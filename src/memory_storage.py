from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
import json
from collections import defaultdict
import logging
from threading import Lock

from .models import UserProfile, AudienceMember, UserEvent, OptimizationSignal, RetargetingEvent
from .config import ProcessingConfig
from .exceptions import StorageError


class MemoryStorage:
    """In-memory storage implementation for demo purposes when Redis is not available"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._lock = Lock()  # Thread safety for concurrent access
        
        # Initialize storage containers
        self.user_profiles: Dict[str, UserProfile] = {}
        self.user_events: Dict[str, List[UserEvent]] = defaultdict(list)
        self.audiences: Dict[str, set] = defaultdict(set)
        self.audience_members: Dict[str, Dict[str, AudienceMember]] = defaultdict(dict)
        self.user_audiences: Dict[str, set] = defaultdict(set)
        self.event_queue: List[UserEvent] = []
        self.optimization_signals: Dict[str, List[OptimizationSignal]] = defaultdict(list)
        self.retargeting_events: List[RetargetingEvent] = []
        
        self.logger.info("Initialized in-memory storage")
    
    # User Profile Operations
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        try:
            with self._lock:
                return self.user_profiles.get(user_id)
        except Exception as e:
            self.logger.error(f"Error getting user profile {user_id}: {e}")
            raise StorageError(f"Failed to get user profile: {e}") from e
    
    def save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile"""
        try:
            with self._lock:
                self.user_profiles[profile.user_id] = profile
        except Exception as e:
            self.logger.error(f"Error saving user profile {profile.user_id}: {e}")
            raise StorageError(f"Failed to save user profile: {e}") from e
    
    def update_user_last_seen(self, user_id: str, timestamp: datetime) -> None:
        """Update user's last seen timestamp"""
        if user_id in self.user_profiles:
            self.user_profiles[user_id].last_seen = timestamp
    
    # Audience Operations
    def add_user_to_audience(self, user_id: str, audience_id: str) -> None:
        """Add user to an audience"""
        member = AudienceMember(user_id=user_id, added_at=datetime.now(timezone.utc))
        self.audiences[audience_id].add(user_id)
        self.audience_members[audience_id][user_id] = member
        self.user_audiences[user_id].add(audience_id)
    
    def remove_user_from_audience(self, user_id: str, audience_id: str) -> None:
        """Remove user from an audience"""
        self.audiences[audience_id].discard(user_id)
        self.audience_members[audience_id].pop(user_id, None)
        self.user_audiences[user_id].discard(audience_id)
    
    def get_audience_members(self, audience_id: str) -> List[AudienceMember]:
        """Get all members of an audience"""
        return list(self.audience_members[audience_id].values())
    
    def get_user_audiences(self, user_id: str) -> List[str]:
        """Get all audiences a user belongs to"""
        return list(self.user_audiences[user_id])
    
    # Event Queue Operations
    def enqueue_event(self, event: UserEvent) -> None:
        """Add event to processing queue"""
        self.event_queue.append(event)
    
    def dequeue_event(self) -> Optional[UserEvent]:
        """Get next event from processing queue"""
        if self.event_queue:
            return self.event_queue.pop(0)
        return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.event_queue)
    
    # Optimization Signals
    def save_optimization_signal(self, signal: OptimizationSignal) -> None:
        """Save optimization signal"""
        try:
            with self._lock:
                self.optimization_signals[signal.user_id].append(signal)
                # Keep only configured max signals per user
                max_signals = self.config.max_signals_per_user
                self.optimization_signals[signal.user_id] = self.optimization_signals[signal.user_id][-max_signals:]
        except Exception as e:
            self.logger.error(f"Error saving optimization signal for {signal.user_id}: {e}")
            raise StorageError(f"Failed to save optimization signal: {e}") from e
    
    def get_user_recent_events(self, user_id: str, hours: int = 24) -> List[UserEvent]:
        """Get user's recent events within specified hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_events = []
        
        for event in self.user_events[user_id]:
            if event.timestamp >= cutoff_time:
                recent_events.append(event)
        
        return recent_events
    
    def save_user_event(self, user_id: str, event: UserEvent) -> None:
        """Save user event for history tracking"""
        try:
            with self._lock:
                self.user_events[user_id].append(event)
                # Keep only configured max events per user
                max_events = self.config.max_events_per_user
                self.user_events[user_id] = self.user_events[user_id][-max_events:]
        except Exception as e:
            self.logger.error(f"Error saving user event for {user_id}: {e}")
            raise StorageError(f"Failed to save user event: {e}") from e
    
    # Retargeting Events
    def save_retargeting_event(self, event: RetargetingEvent) -> None:
        """Save retargeting event"""
        self.retargeting_events.append(event)
    
    # Health Check
    def ping(self) -> bool:
        """Check if storage is available"""
        return True