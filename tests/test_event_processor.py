"""
Tests for event processing logic
"""
import pytest
from datetime import datetime, timezone

from src.event_processor import EventProcessor
from src.memory_storage import MemoryStorage
from src.models import UserEvent, EventType


class TestEventProcessor:
    """Test EventProcessor functionality"""
    
    def test_process_single_event(self, event_processor: EventProcessor, sample_user_event: UserEvent):
        """Test processing a single event creates user profile"""
        # Process the event
        event_processor.process_event(sample_user_event)
        
        # Check that user profile was created
        profile = event_processor.storage.get_user_profile(sample_user_event.user_id)
        assert profile is not None
        assert profile.user_id == sample_user_event.user_id
        assert len(profile.last_events) == 1
        
    def test_cart_abandoner_audience(self, event_processor: EventProcessor, cart_event: UserEvent):
        """Test that cart addition adds user to cart abandoners audience"""
        # Process cart event
        event_processor.process_event(cart_event)
        
        # Check audiences
        audiences = event_processor.storage.get_user_audiences(cart_event.user_id)
        assert "cart_abandoners" in audiences
    
    def test_video_non_converter_audience(self, event_processor: EventProcessor, video_event: UserEvent):
        """Test that video watch adds user to video non-converters audience"""
        # Process video event with high completion
        event_processor.process_event(video_event)
        
        # Check audiences
        audiences = event_processor.storage.get_user_audiences(video_event.user_id)
        assert "video_non_converters" in audiences
    
    def test_intent_score_calculation(self, event_processor: EventProcessor, cart_event: UserEvent):
        """Test that intent score increases with engagement"""
        # Process cart event (high intent activity)
        event_processor.process_event(cart_event)
        
        # Check profile
        profile = event_processor.storage.get_user_profile(cart_event.user_id)
        assert profile.high_intent_score > 0.0
        assert profile.propensity_to_convert > 0.0
    
    def test_purchase_removes_from_cart_abandoners(self, event_processor: EventProcessor):
        """Test that purchase removes user from cart abandoners"""
        user_id = "purchase_user"
        
        # First add to cart
        cart_event = UserEvent(
            user_id=user_id,
            event_type=EventType.ADD_TO_CART,
            timestamp=datetime.now(timezone.utc),
            properties={"product_name": "test"}
        )
        event_processor.process_event(cart_event)
        
        # Verify in cart abandoners
        audiences = event_processor.storage.get_user_audiences(user_id)
        assert "cart_abandoners" in audiences
        
        # Then purchase
        purchase_event = UserEvent(
            user_id=user_id,
            event_type=EventType.PURCHASE,
            timestamp=datetime.now(timezone.utc),
            properties={"order_id": "test_order", "total_amount": 99.99}
        )
        event_processor.process_event(purchase_event)
        
        # Verify removed from cart abandoners
        audiences = event_processor.storage.get_user_audiences(user_id)
        assert "cart_abandoners" not in audiences