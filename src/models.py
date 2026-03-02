from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from enum import Enum


class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    VIDEO_WATCH = "video_watch"
    SIGN_UP = "sign_up"


class UserEvent(BaseModel):
    """Represents a user engagement event"""
    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    event_type: EventType = Field(..., description="Type of user event")
    timestamp: datetime = Field(..., description="Event timestamp (timezone-aware)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event-specific properties")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class UserProfile(BaseModel):
    """User profile with engagement history and scores"""
    user_id: str = Field(..., min_length=1, description="Unique user identifier")
    last_seen: datetime = Field(..., description="Last activity timestamp")
    last_events: List[UserEvent] = Field(default_factory=list, description="Recent user events")
    high_intent_score: float = Field(default=0.0, ge=0.0, le=1.0, description="User intent score (0-1)")
    propensity_to_convert: float = Field(default=0.0, ge=0.0, le=1.0, description="Conversion propensity (0-1)") 
    audiences: List[str] = Field(default_factory=list, description="Audience memberships")
    
    @field_validator('last_seen')
    @classmethod
    def validate_last_seen(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class AudienceDefinition(BaseModel):
    """Definition of a retargeting audience"""
    audience_id: str = Field(..., min_length=1, description="Unique audience identifier")
    name: str = Field(..., min_length=1, description="Human-readable audience name")
    description: str = Field(..., description="Audience description")
    conditions: Dict[str, Any] = Field(..., description="Audience membership conditions")


class AudienceMember(BaseModel):
    """Represents a user's membership in an audience"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    added_at: datetime = Field(..., description="When user was added to audience")
    
    @field_validator('added_at')
    @classmethod
    def validate_added_at(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class OptimizationSignal(BaseModel):
    """Optimization signal for ad platforms"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    signal_type: str = Field(..., min_length=1, description="Type of optimization signal")
    value: float = Field(..., description="Signal value")
    timestamp: datetime = Field(..., description="Signal generation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional signal metadata")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class RetargetingEvent(BaseModel):
    """Event for audience membership changes"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    audience_id: str = Field(..., min_length=1, description="Audience identifier")
    action: Literal["add", "remove"] = Field(..., description="Add or remove action")
    timestamp: datetime = Field(..., description="Event timestamp")
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware"""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v