"""
Configuration management for the Real-Time Retargeting & Optimization Signals Service
"""
import os
from typing import Dict, Any
from pydantic import BaseModel, Field


class RedisConfig(BaseModel):
    """Redis configuration settings"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port") 
    db: int = Field(default=0, description="Redis database number")
    password: str = Field(default="", description="Redis password")
    socket_timeout: float = Field(default=5.0, description="Redis socket timeout")
    socket_connect_timeout: float = Field(default=5.0, description="Redis connect timeout")


class ServerConfig(BaseModel):
    """Server configuration settings"""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Log level")
    reload: bool = Field(default=False, description="Auto-reload on changes")


class ProcessingConfig(BaseModel):
    """Event processing configuration"""
    max_events_per_user: int = Field(default=1000, description="Max events stored per user")
    max_user_history_events: int = Field(default=50, description="Max events in user profile")
    max_signals_per_user: int = Field(default=100, description="Max optimization signals per user")  
    batch_size: int = Field(default=10, description="Worker batch size")
    poll_interval: float = Field(default=1.0, description="Worker polling interval")
    
    # Audience thresholds
    cart_abandonment_hours: int = Field(default=24, description="Hours for cart abandonment")
    video_completion_threshold: float = Field(default=0.75, description="Video watch threshold")
    high_intent_threshold: float = Field(default=0.7, description="High intent score threshold")


class AppConfig(BaseModel):
    """Application configuration"""
    redis: RedisConfig = RedisConfig()
    server: ServerConfig = ServerConfig()
    processing: ProcessingConfig = ProcessingConfig()
    
    # Service metadata
    service_name: str = "Real-Time Retargeting & Optimization Signals Service"
    version: str = "1.0.0"
    description: str = "A service that turns raw user events into retargeting audiences and optimization signals in real time"


def load_config() -> AppConfig:
    """Load configuration from environment variables and defaults"""
    return AppConfig(
        redis=RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", ""),
        ),
        server=ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", 8000)),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            reload=os.getenv("SERVER_RELOAD", "false").lower() == "true",
        ),
        processing=ProcessingConfig(
            max_events_per_user=int(os.getenv("MAX_EVENTS_PER_USER", 1000)),
            max_user_history_events=int(os.getenv("MAX_USER_HISTORY_EVENTS", 50)),
            max_signals_per_user=int(os.getenv("MAX_SIGNALS_PER_USER", 100)),
            batch_size=int(os.getenv("WORKER_BATCH_SIZE", 10)),
            poll_interval=float(os.getenv("WORKER_POLL_INTERVAL", 1.0)),
            cart_abandonment_hours=int(os.getenv("CART_ABANDONMENT_HOURS", 24)),
            video_completion_threshold=float(os.getenv("VIDEO_COMPLETION_THRESHOLD", 0.75)),
            high_intent_threshold=float(os.getenv("HIGH_INTENT_THRESHOLD", 0.7)),
        )
    )


# Global config instance
config = load_config()