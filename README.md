# Real-Time Retargeting & Optimization Signals Service

A high-performance service that transforms raw user events into actionable retargeting audiences and optimization signals in near real-time.

## Features

### 🎯 Event Stream Processing
- Handles multiple event types: `page_view`, `add_to_cart`, `purchase`, `video_watch`, `sign_up`
- Real-time event ingestion via REST API
- Batch event processing for high throughput

### 🎪 Retargeting Audiences
- **Cart Abandoners**: Users who added items but didn't purchase within 24h
- **Video Non-Converters**: Users who watched 75%+ of video but didn't sign up
- **High Intent Users**: Users with calculated intent score > 0.7

### 📊 Optimization Signals
- **High Intent Score**: Based on user activity patterns and engagement
- **Propensity to Convert**: Calculated using behavioral heuristics
- Real-time signal updates as user behavior changes

### 🔐 Identity & Attribution
- User normalization by hashed email or internal user_id
- Persistent user profiles with event history
- Last seen timestamps and activity tracking

## Quick Start

### Prerequisites
- Python 3.8+
- Redis (via Docker or local installation) - *Optional, service works with in-memory fallback*

### 1. Setup Environment
```bash
# Clone and setup
git clone <repository>
cd "SignalStream Retargeting & Optimization Engine"

# Create virtual environment (recommended)
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix/Mac: source .venv/bin/activate

# Or use make for convenience
make setup
```

### 2. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Or use make
make install
```

### 3. Configure Environment (Optional)
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file for custom configuration
# Default values work out-of-the-box
```

### 4. Start Redis (Optional)
```bash
# Using Docker Compose (recommended)
docker-compose up -d redis

# Or use make
make docker-up

# Note: Service will use in-memory storage if Redis is unavailable
```

### 5. Start the Service
```bash
# Start service with demo
python start.py --demo

# Or use make
make run-demo

# Custom configuration
python start.py --host 127.0.0.1 --port 9000 --demo
```
# Terminal 1: Start the API server
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start the background worker (optional for demo)
python -m src.worker
```

## ✨ New Feature Highlights

### 🔧 Configuration Management
- **Environment Variables**: Centralized configuration through `.env` file
- **Type Safety**: Pydantic-based configuration with validation
- **Defaults**: Service works out-of-the-box without configuration
- **Flexibility**: Override any setting via environment variables

### 🛡️ Enhanced Error Handling
- **Custom Exceptions**: Specific exception types for different error scenarios
- **Graceful Degradation**: Automatic fallback to in-memory storage if Redis unavailable
- **Comprehensive Logging**: Structured logging with configurable levels
- **Validation**: Input validation with detailed error messages

### 🧪 Testing Infrastructure
- **Unit Tests**: Comprehensive test coverage for all components
- **Fixtures**: Reusable test fixtures for consistent testing
- **Integration Tests**: End-to-end testing of complete workflows
- **Test Automation**: Make commands for easy test execution

### 🚀 Development Workflow
- **Makefile**: Common development tasks automated
- **Hot Reload**: Automatic service restart on code changes
- **Docker Support**: Containerized Redis with docker-compose
- **Virtual Environment**: Isolated Python environment management

### 4. Test the Service
```bash
# Health check
curl http://localhost:8000/

# Generate demo events
curl -X POST http://localhost:8000/v1/demo/generate-events?count=50

# Simulate user journey
curl -X POST http://localhost:8000/v1/demo/user-journey
```

## API Documentation

### Event Ingestion

#### POST `/v1/events`
Ingest a single user event.

```json
{
  "user_id": "abc123def456",
  "event_type": "add_to_cart",
  "timestamp": "2024-03-02T10:30:00Z",
  "properties": {
    "product_id": "prod_789",
    "product_name": "laptop",
    "price": 1299.99,
    "quantity": 1
  }
}
```

#### POST `/v1/events/batch`
Ingest multiple events at once.

### Audience Management

#### GET `/v1/audiences`
List all available audiences with member counts.

#### GET `/v1/audiences/{audience_id}/members`
Get current members of a specific audience.

```json
[
  {
    "user_id": "abc123def456",
    "added_at": "2024-03-02T10:35:00Z"
  }
]
```

#### DELETE `/v1/audiences/{audience_id}/members/{user_id}`
Remove a user from an audience.

### User Profiles

#### GET `/v1/users/{user_id}/profile`
Get user's complete profile with scores and audiences.

```json
{
  "user_id": "abc123def456",
  "last_seen": "2024-03-02T10:35:00Z",
  "high_intent_score": 0.75,
  "propensity_to_convert": 0.68,
  "audiences": ["cart_abandoners", "high_intent"],
  "last_events": [...]
}
```

#### GET `/v1/users/{user_id}/events?hours=24`
Get user's recent events within specified timeframe.

#### GET `/v1/users/{user_id}/audiences`
Get all audiences a user belongs to.

### Demo & Testing

#### POST `/v1/demo/generate-events?count=100`
Generate realistic demo events for testing.

#### POST `/v1/demo/user-journey`
Simulate a complete user journey with realistic event patterns.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Event Source  │───▶│   FastAPI App   │───▶│   Redis Queue   │
│  (API/Stream)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Background      │
                       │ Worker          │
                       │                 │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Event Processor │───▶│ User Profiles   │
                       │                 │    │ & Audiences     │
                       └─────────────────┘    └─────────────────┘
```

### Components

1. **FastAPI Application**: REST API for event ingestion and data access
2. **Redis Storage**: Event queuing, user profiles, and audience membership
3. **Event Processor**: Core logic for audience building and signal generation
4. **Background Worker**: Asynchronous event processing
5. **Event Generator**: Demo data simulation

## 🏗️ Enhanced Architecture & Code Quality

### Configuration Layer
- **`src/config.py`**: Centralized configuration management using Pydantic models
- **Environment Variables**: Support for `.env` files and runtime configuration
- **Type Safety**: All configuration values validated at startup
- **Defaults**: Production-ready defaults that work out-of-the-box

### Error Handling & Resilience
- **Custom Exceptions**: Specific exception types in `src/exceptions.py`
- **Graceful Degradation**: Automatic fallback to in-memory storage
- **Structured Logging**: Configurable logging with proper formatting
- **Input Validation**: Comprehensive Pydantic model validation

### Storage Abstraction
- **Dual Storage**: Redis primary with memory fallback (`src/storage.py`, `src/memory_storage.py`)
- **Thread Safety**: Proper locking for concurrent access
- **Connection Pooling**: Efficient Redis connection management
- **Automatic Retry**: Built-in retry logic for transient failures

### Testing Infrastructure
- **`tests/`**: Comprehensive test suite with fixtures
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow validation
- **Test Automation**: Make targets for easy test execution

### Development Workflow
- **Hot Reload**: Automatic restart on code changes
- **Docker Integration**: Containerized Redis with docker-compose
- **Make Targets**: Automated common development tasks
- **Code Quality**: Consistent formatting and structure

### Production Features
- **Health Checks**: Comprehensive service health monitoring
- **Metrics**: Built-in performance and business metrics
- **Configuration Validation**: Startup validation of all settings
- **Error Reporting**: Structured error responses with proper HTTP codes

## Event Types & Properties

### Page View
```json
{
  "event_type": "page_view",
  "properties": {
    "page_url": "/products",
    "referrer": "google",
    "time_on_page": 120
  }
}
```

### Add to Cart
```json
{
  "event_type": "add_to_cart", 
  "properties": {
    "product_id": "prod_123",
    "product_name": "laptop",
    "price": 1299.99,
    "quantity": 1,
    "category": "electronics"
  }
}
```

### Purchase
```json
{
  "event_type": "purchase",
  "properties": {
    "order_id": "order_12345",
    "total_amount": 1299.99,
    "payment_method": "credit_card",
    "items_count": 2
  }
}
```

### Video Watch
```json
{
  "event_type": "video_watch",
  "properties": {
    "video_id": "video_42",
    "watch_percentage": 0.85,
    "duration_seconds": 300,
    "quality": "1080p"
  }
}
```

### Sign Up
```json
{
  "event_type": "sign_up",
  "properties": {
    "signup_method": "email",
    "user_type": "individual",
    "referral_code": "ref_1234"
  }
}
```

## Scoring Algorithms

### High Intent Score
Calculated based on weighted recent activities:
- Page View: 0.1
- Video Watch: 0.4 (× watch percentage)
- Add to Cart: 0.6
- Sign Up: 0.8
- Purchase: 1.0

Score is normalized to 0-1 range.

### Propensity to Convert
Heuristic model considering:
- High intent score (40%)
- Recent session activity (30%)
- Cart additions (20%)
- Video engagement (10%)

## Audience Definitions

### Cart Abandoners (24h)
- **Condition**: Has `add_to_cart` event but no `purchase` within 24 hours
- **Use Case**: Retargeting campaigns with cart recovery offers

### Video Non-Converters
- **Condition**: Watched 75%+ of video but no `sign_up` within 48 hours
- **Use Case**: Educational content retargeting

### High Intent Users
- **Condition**: High intent score > 0.7
- **Use Case**: Premium targeting for high-value campaigns

## Webhook Integration

### Ad Platform Callback (Optional)
```bash
# Simulated webhook endpoint
POST /v1/webhooks/ad-platform

# Payload example
{
  "user_id": "abc123",
  "audience_id": "cart_abandoners", 
  "action": "add",
  "timestamp": "2024-03-02T10:35:00Z"
}
```

## Production Considerations

### Scaling
- **Horizontal**: Multiple worker instances processing from Redis queue
- **Vertical**: Increase worker batch sizes and processing intervals
- **Storage**: Redis Cluster for high-volume deployments

### Monitoring
- Queue depth monitoring
- Processing latency metrics
- Audience growth rates
- Score distribution analytics

### Security
- API authentication (implement JWT/OAuth)
- Rate limiting for event ingestion
- User data encryption at rest

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Code Structure
```
src/
├── main.py              # FastAPI application
├── models.py            # Pydantic data models
├── storage.py           # Redis storage layer
├── event_processor.py   # Core business logic
├── event_generator.py   # Demo event simulation
└── worker.py           # Background processing