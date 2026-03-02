import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Union

from .models import UserEvent, UserProfile, EventType, OptimizationSignal, RetargetingEvent
from .storage import RedisStorage
from .memory_storage import MemoryStorage
from .config import ProcessingConfig
from .exceptions import ProcessingError, UserProfileNotFoundError


class EventProcessor:
    """Processes user events to build audiences and generate optimization signals"""
    
    def __init__(self, storage: Union[RedisStorage, MemoryStorage], config: ProcessingConfig):
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Audience definitions - configurable thresholds
        self.audience_definitions = {
            "cart_abandoners": {
                "name": "Cart Abandoners 24h",
                "description": f"Users who added to cart but no purchase in {config.cart_abandonment_hours}h",
                "conditions": {
                    "has_event": "add_to_cart",
                    "missing_event": "purchase",
                    "timeframe_hours": config.cart_abandonment_hours
                }
            },
            "video_non_converters": {
                "name": "Video Watchers Non-Converters",
                "description": f"Users who watched {int(config.video_completion_threshold*100)}% of video but did not sign up",
                "conditions": {
                    "has_event": "video_watch",
                    "missing_event": "sign_up",
                    "watch_threshold": config.video_completion_threshold,
                    "timeframe_hours": 48
                }
            },
            "high_intent": {
                "name": "High Intent Users",
                "description": f"Users with high intent score >{config.high_intent_threshold}",
                "conditions": {
                    "score_threshold": config.high_intent_threshold,
                    "score_type": "high_intent_score"
                }
            }
        }
    
    def process_event(self, event: UserEvent) -> None:
        """Process a single user event"""
        try:
            # Ensure event timestamp is timezone aware
            event_timestamp = event.timestamp
            if event_timestamp.tzinfo is None:
                event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
            
            # Get or create user profile
            profile = self.storage.get_user_profile(event.user_id)
            if not profile:
                profile = UserProfile(
                    user_id=event.user_id,
                    last_seen=event_timestamp,
                    last_events=[],
                    high_intent_score=0.0,
                    propensity_to_convert=0.0,
                    audiences=[]
                )
            
            # Update profile with new event
            profile.last_seen = event_timestamp
            profile.last_events.append(event)
            # Keep only configured max events in profile
            max_events = self.config.max_user_history_events
            profile.last_events = profile.last_events[-max_events:]
            
            # Save event to storage
            self.storage.save_user_event(event.user_id, event)
            
            # Update user scores
            self._update_user_scores(profile, event)
            
            # Process audiences
            self._process_audiences(profile, event)
            
            # Save updated profile
            self.storage.save_user_profile(profile)
            
            self.logger.info(f"Processed event {event.event_type} for user {event.user_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing event {event.event_type} for user {event.user_id}: {e}")
            raise ProcessingError(f"Failed to process event: {e}") from e
    
    def _update_user_scores(self, profile: UserProfile, event: UserEvent) -> None:
        """Update user intent and conversion scores"""
        # Calculate high intent score based on recent activity
        intent_weights = {
            EventType.PAGE_VIEW: 0.1,
            EventType.ADD_TO_CART: 0.6,
            EventType.VIDEO_WATCH: 0.4,
            EventType.PURCHASE: 1.0,
            EventType.SIGN_UP: 0.8
        }
        
        # Get recent events (last 24 hours)
        recent_events = self._get_recent_events(profile, hours=24)
        
        # Calculate intent score
        total_score = 0.0
        for evt in recent_events:
            weight = intent_weights.get(evt.event_type, 0.0)
            # Add bonus for video watch completion
            if evt.event_type == EventType.VIDEO_WATCH and "watch_percentage" in evt.properties:
                weight *= evt.properties["watch_percentage"]
            total_score += weight
        
        # Normalize score to 0-1 range
        profile.high_intent_score = min(total_score / 5.0, 1.0)
        
        # Calculate propensity to convert using simple heuristic
        profile.propensity_to_convert = self._calculate_conversion_propensity(profile)
        
        # Emit optimization signals
        self._emit_optimization_signals(profile)
        
        self.logger.info(f"Updated profile for user {profile.user_id}, intent: {profile.high_intent_score:.2f}, conversion: {profile.propensity_to_convert:.2f}")
    
    def _calculate_conversion_propensity(self, profile: UserProfile) -> float:
        """Calculate propensity to convert using heuristic model"""
        try:
            # Simple features for conversion prediction
            features = []
            
            # Feature 1: High intent score
            features.append(profile.high_intent_score)
            
            # Feature 2: Number of sessions in last 7 days
            recent_events = self._get_recent_events(profile, hours=168)  # 7 days
            page_views = len([e for e in recent_events if e.event_type == EventType.PAGE_VIEW])
            features.append(min(page_views / 10.0, 1.0))  # Normalize
            
            # Feature 3: Has added to cart recently
            has_cart = any(e.event_type == EventType.ADD_TO_CART for e in recent_events)
            features.append(1.0 if has_cart else 0.0)
            
            # Feature 4: Video engagement
            video_events = [e for e in recent_events if e.event_type == EventType.VIDEO_WATCH]
            avg_watch_pct = 0.0
            if video_events:
                watch_pcts = [e.properties.get("watch_percentage", 0.0) for e in video_events]
                avg_watch_pct = sum(watch_pcts) / len(watch_pcts)
            features.append(avg_watch_pct)
            
            # Simple logistic function
            score = sum(features) / len(features)
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating conversion propensity: {e}")
            return 0.0
    
    def _get_recent_events(self, profile: UserProfile, hours: int = 24) -> List[UserEvent]:
        """Get user's recent events from storage"""
        return self.storage.get_user_recent_events(profile.user_id, hours)
    
    def _process_audiences(self, profile: UserProfile, event: UserEvent) -> None:
        """Process audience membership for user"""
        for audience_id, definition in self.audience_definitions.items():
            should_be_in_audience = self._evaluate_audience_condition(
                profile, event, definition["conditions"]
            )
            
            current_audiences = self.storage.get_user_audiences(profile.user_id)
            is_in_audience = audience_id in current_audiences
            
            if should_be_in_audience and not is_in_audience:
                # Add to audience
                self.storage.add_user_to_audience(profile.user_id, audience_id)
                self._emit_retargeting_event(profile.user_id, audience_id, "add")
                self.logger.info(f"Added user {profile.user_id} to audience {audience_id}")
                
            elif not should_be_in_audience and is_in_audience:
                # Remove from audience
                self.storage.remove_user_from_audience(profile.user_id, audience_id)
                self._emit_retargeting_event(profile.user_id, audience_id, "remove")
                self.logger.info(f"Removed user {profile.user_id} from audience {audience_id}")
    
    def _evaluate_audience_condition(self, profile: UserProfile, event: UserEvent, conditions: Dict[str, Any]) -> bool:
        """Evaluate if user meets audience conditions"""
        try:
            if "score_threshold" in conditions:
                # Score-based audience
                score_type = conditions["score_type"]
                threshold = conditions["score_threshold"]
                
                if score_type == "high_intent_score":
                    return profile.high_intent_score >= threshold
                elif score_type == "propensity_to_convert":
                    return profile.propensity_to_convert >= threshold
                    
            elif "has_event" in conditions:
                # Event-based audience
                required_event = conditions["has_event"]
                missing_event = conditions.get("missing_event")
                timeframe_hours = conditions.get("timeframe_hours", 24)
                
                recent_events = self._get_recent_events(profile, timeframe_hours)
                
                # Check if has required event
                has_required = any(e.event_type.value == required_event for e in recent_events)
                if not has_required:
                    return False
                
                # Check if missing the exclusion event
                if missing_event:
                    has_missing = any(e.event_type.value == missing_event for e in recent_events)
                    if has_missing:
                        return False
                
                # Special case for video watch threshold
                if required_event == "video_watch" and "watch_threshold" in conditions:
                    threshold = conditions["watch_threshold"]
                    video_events = [e for e in recent_events if e.event_type == EventType.VIDEO_WATCH]
                    if video_events:
                        max_watch_pct = max(e.properties.get("watch_percentage", 0.0) for e in video_events)
                        return max_watch_pct >= threshold
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error evaluating audience condition: {e}")
            return False
    
    def _emit_optimization_signals(self, profile: UserProfile) -> None:
        """Emit optimization signals"""
        signals = [
            OptimizationSignal(
                user_id=profile.user_id,
                signal_type="high_intent_score",
                value=profile.high_intent_score,
                timestamp=datetime.now(timezone.utc),
                metadata={"last_updated": profile.last_seen.isoformat()}
            ),
            OptimizationSignal(
                user_id=profile.user_id,
                signal_type="propensity_to_convert",
                value=profile.propensity_to_convert,
                timestamp=datetime.now(timezone.utc),
                metadata={"last_updated": profile.last_seen.isoformat()}
            )
        ]
        
        for signal in signals:
            self.storage.save_optimization_signal(signal)
    
    def _emit_retargeting_event(self, user_id: str, audience_id: str, action: str) -> None:
        """Emit retargeting event"""
        retargeting_event = RetargetingEvent(
            user_id=user_id,
            audience_id=audience_id,
            action=action,
            timestamp=datetime.now(timezone.utc)
        )
        self.storage.save_retargeting_event(retargeting_event)