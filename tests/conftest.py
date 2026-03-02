"""
Test configuration and fixtures for the retargeting service
"""
import pytest
from datetime import datetime, timezone
from typing import Generator

from src.config import ProcessingConfig
from src.memory_storage import MemoryStorage
from src.event_processor import EventProcessor
from src.models import UserEvent, EventType


@pytest.fixture
def test_config() -> ProcessingConfig:
    """Test configuration with reduced limits for faster testing"""
    return ProcessingConfig(
        max_events_per_user=100,
        max_user_history_events=10,
        max_signals_per_user=20,
        batch_size=5,
        poll_interval=0.1,
        cart_abandonment_hours=1,  # Reduced for testing
        video_completion_threshold=0.75,
        high_intent_threshold=0.7
    )


@pytest.fixture
def memory_storage(test_config: ProcessingConfig) -> MemoryStorage:
    """In-memory storage for testing"""
    return MemoryStorage(test_config)


@pytest.fixture
def event_processor(memory_storage: MemoryStorage, test_config: ProcessingConfig) -> EventProcessor:
    """Event processor with test configuration"""
    return EventProcessor(memory_storage, test_config)


@pytest.fixture
def sample_user_event() -> UserEvent:
    """Sample user event for testing"""
    return UserEvent(
        user_id="test_user_123",
        event_type=EventType.PAGE_VIEW,
        timestamp=datetime.now(timezone.utc),
        properties={"page_url": "/home", "referrer": "google"}
    )


@pytest.fixture
def cart_event() -> UserEvent:
    """Cart addition event for testing"""
    return UserEvent(
        user_id="test_user_123",
        event_type=EventType.ADD_TO_CART,
        timestamp=datetime.now(timezone.utc),
        properties={"product_name": "laptop", "price": 1299.99}
    )


@pytest.fixture
def video_event() -> UserEvent:
    """Video watch event for testing"""
    return UserEvent(
        user_id="test_user_123", 
        event_type=EventType.VIDEO_WATCH,
        timestamp=datetime.now(timezone.utc),
        properties={"watch_percentage": 0.85, "video_title": "Product Demo"}
    )