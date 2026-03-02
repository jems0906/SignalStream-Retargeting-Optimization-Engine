import random
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Union
import logging

from .models import UserEvent, EventType
from .storage import RedisStorage
from .memory_storage import MemoryStorage
from .config import ProcessingConfig
from .exceptions import StorageError


class EventGenerator:
    """Generates realistic user events for testing and demonstration"""
    
    def __init__(self, storage: Union[RedisStorage, MemoryStorage], config: ProcessingConfig, user_pool_size: int = 100):
        self.storage = storage
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.user_pool = self._generate_user_pool(user_pool_size)
        
    def _generate_user_pool(self, count: int) -> List[str]:
        """Generate a pool of user IDs"""
        users = []
        for i in range(count):
            # Generate hashed email-like user IDs
            email = f"user{i}@example.com"
            user_id = hashlib.md5(email.encode()).hexdigest()[:12]
            users.append(user_id)
        return users
    
    def generate_realistic_event_stream(self, duration_minutes: int = 60) -> None:
        """Generate realistic events for specified duration"""
        print(f"Starting event generation for {duration_minutes} minutes...")
        
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now(timezone.utc) < end_time:
            # Generate 1-5 events per second
            events_count = random.randint(1, 5)
            
            for _ in range(events_count):
                event = self._generate_single_event()
                self.storage.enqueue_event(event)
            
            # Wait for next batch
            time.sleep(1)
            
            # Print progress every 10 seconds
            if int(time.time()) % 10 == 0:
                queue_size = self.storage.get_queue_size()
                print(f"Generated events. Queue size: {queue_size}")
    
    def generate_batch_events(self, count: int) -> List[UserEvent]:
        """Generate a batch of events"""
        events = []
        for _ in range(count):
            event = self._generate_single_event()
            events.append(event)
            self.storage.enqueue_event(event)
        return events
    
    def _generate_single_event(self) -> UserEvent:
        """Generate a single realistic user event"""
        user_id = random.choice(self.user_pool)
        
        # Weight the event types for realistic distribution
        event_weights = {
            EventType.PAGE_VIEW: 0.5,      # Most common
            EventType.ADD_TO_CART: 0.2,    # Moderate
            EventType.VIDEO_WATCH: 0.15,   # Moderate
            EventType.SIGN_UP: 0.1,        # Less common
            EventType.PURCHASE: 0.05       # Least common
        }
        
        event_type = random.choices(
            list(event_weights.keys()),
            weights=list(event_weights.values()),
            k=1
        )[0]
        
        # Generate event properties based on type
        properties = self._generate_event_properties(event_type)
        
        # Add some randomness to timestamps (within last hour)
        timestamp = datetime.now(timezone.utc) - timedelta(
            seconds=random.randint(0, 3600)
        )
        
        return UserEvent(
            user_id=user_id,
            event_type=event_type,
            timestamp=timestamp,
            properties=properties
        )
    
    def _generate_event_properties(self, event_type: EventType) -> Dict[str, Any]:
        """Generate realistic properties for event types"""
        properties = {}
        
        if event_type == EventType.PAGE_VIEW:
            pages = ["/home", "/products", "/about", "/pricing", "/blog", "/contact"]
            properties = {
                "page_url": random.choice(pages),
                "referrer": random.choice(["google", "facebook", "direct", "email"]),
                "time_on_page": random.randint(10, 300)  # seconds
            }
            
        elif event_type == EventType.ADD_TO_CART:
            products = ["laptop", "phone", "headphones", "tablet", "camera"]
            properties = {
                "product_id": f"prod_{random.randint(100, 999)}",
                "product_name": random.choice(products),
                "price": round(random.uniform(50, 2000), 2),
                "quantity": random.randint(1, 3),
                "category": random.choice(["electronics", "accessories", "computers"])
            }
            
        elif event_type == EventType.PURCHASE:
            properties = {
                "order_id": f"order_{random.randint(10000, 99999)}",
                "total_amount": round(random.uniform(100, 5000), 2),
                "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),
                "items_count": random.randint(1, 5)
            }
            
        elif event_type == EventType.VIDEO_WATCH:
            properties = {
                "video_id": f"video_{random.randint(1, 100)}",
                "video_title": f"Video Title {random.randint(1, 100)}",
                "watch_percentage": round(random.uniform(0.1, 1.0), 2),
                "duration_seconds": random.randint(60, 1800),  # 1-30 minutes
                "quality": random.choice(["720p", "1080p", "4k"])
            }
            
        elif event_type == EventType.SIGN_UP:
            properties = {
                "signup_method": random.choice(["email", "google", "facebook", "apple"]),
                "user_type": random.choice(["individual", "business"]),
                "referral_code": f"ref_{random.randint(1000, 9999)}" if random.random() > 0.7 else None
            }
        
        return properties
    
    def simulate_user_journey(self, user_id: str = None) -> List[UserEvent]:
        """Simulate a realistic user journey"""
        if not user_id:
            user_id = random.choice(self.user_pool)
            
        journey_events = []
        base_time = datetime.now(timezone.utc)
        
        # Journey patterns
        patterns = [
            "browser_converter",    # Browse -> Add to Cart -> Purchase
            "video_viewer",        # Video Watch -> Sign up
            "cart_abandoner",      # Browse -> Add to Cart -> Leave
            "casual_browser"       # Just browse around
        ]
        
        pattern = random.choice(patterns)
        
        if pattern == "browser_converter":
            # Browse -> Add to Cart -> Purchase journey
            events = [
                (EventType.PAGE_VIEW, {"page_url": "/home"}),
                (EventType.PAGE_VIEW, {"page_url": "/products"}),
                (EventType.ADD_TO_CART, {"product_name": "laptop", "price": 1299.99}),
                (EventType.PAGE_VIEW, {"page_url": "/checkout"}),
                (EventType.PURCHASE, {"total_amount": 1299.99, "order_id": f"order_{random.randint(10000, 99999)}"})
            ]
            
        elif pattern == "video_viewer":
            # Video engagement journey
            events = [
                (EventType.PAGE_VIEW, {"page_url": "/videos"}),
                (EventType.VIDEO_WATCH, {"watch_percentage": 0.8, "video_title": "Product Demo"}),
                (EventType.SIGN_UP, {"signup_method": "email"})
            ]
            
        elif pattern == "cart_abandoner":
            # Cart abandonment journey
            events = [
                (EventType.PAGE_VIEW, {"page_url": "/products"}),
                (EventType.ADD_TO_CART, {"product_name": "phone", "price": 899.99}),
                (EventType.PAGE_VIEW, {"page_url": "/cart"}),
                # No purchase - abandoned
            ]
            
        else:  # casual_browser
            # Just browsing
            pages = ["/home", "/about", "/blog", "/pricing"]
            events = [(EventType.PAGE_VIEW, {"page_url": page}) for page in random.sample(pages, 3)]
        
        # Create events with realistic timing
        for i, (event_type, properties) in enumerate(events):
            timestamp = base_time + timedelta(minutes=i * random.randint(1, 5))
            event = UserEvent(
                user_id=user_id,
                event_type=event_type,
                timestamp=timestamp,
                properties=properties
            )
            journey_events.append(event)
            self.storage.enqueue_event(event)
        
        return journey_events