"""
Tests for core models and validation
"""
from datetime import datetime, timezone
from pydantic import ValidationError
import pytest

from src.models import UserEvent, EventType, UserProfile, AudienceMember


class TestUserEvent:
    """Test UserEvent model"""
    
    def test_valid_user_event(self):
        """Test creating a valid user event"""
        event = UserEvent(
            user_id="test_user",
            event_type=EventType.PAGE_VIEW,
            timestamp=datetime.now(timezone.utc),
            properties={"page_url": "/home"}
        )
        assert event.user_id == "test_user"
        assert event.event_type == EventType.PAGE_VIEW
        assert event.properties["page_url"] == "/home"
    
    def test_timezone_validation(self):
        """Test that naive timestamps get timezone added"""
        naive_time = datetime.now()  # No timezone
        event = UserEvent(
            user_id="test_user",
            event_type=EventType.PAGE_VIEW,
            timestamp=naive_time
        )
        # Should have timezone after validation
        assert event.timestamp.tzinfo is not None
    
    def test_empty_user_id_validation(self):
        """Test that empty user_id is rejected"""
        with pytest.raises(ValidationError):
            UserEvent(
                user_id="",  # Empty string should fail
                event_type=EventType.PAGE_VIEW,
                timestamp=datetime.now(timezone.utc)
            )


class TestUserProfile:
    """Test UserProfile model"""
    
    def test_valid_user_profile(self):
        """Test creating a valid user profile"""
        profile = UserProfile(
            user_id="test_user",
            last_seen=datetime.now(timezone.utc),
            high_intent_score=0.5,
            propensity_to_convert=0.3
        )
        assert profile.user_id == "test_user"
        assert 0.0 <= profile.high_intent_score <= 1.0
        assert 0.0 <= profile.propensity_to_convert <= 1.0
    
    def test_score_validation(self):
        """Test that scores are constrained to [0, 1] range"""
        with pytest.raises(ValidationError):
            UserProfile(
                user_id="test_user",
                last_seen=datetime.now(timezone.utc),
                high_intent_score=1.5  # Should fail - too high
            )
        
        with pytest.raises(ValidationError):
            UserProfile(
                user_id="test_user",
                last_seen=datetime.now(timezone.utc),
                propensity_to_convert=-0.1  # Should fail - negative
            )