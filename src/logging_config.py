"""
Logging configuration for the Real-Time Retargeting & Optimization Signals Service
"""
import logging
import sys
from typing import Dict, Any


def setup_logging(log_level: str = "INFO", log_format: str = None) -> None:
    """Setup application logging configuration"""
    
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout
    )
    
    # Set specific logger levels
    loggers_config = {
        "uvicorn": "INFO",
        "uvicorn.error": "INFO", 
        "uvicorn.access": "WARNING",
        "fastapi": "INFO",
        "redis": "WARNING",
    }
    
    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level))
    
    # Create application logger
    app_logger = logging.getLogger("retargeting_service")
    app_logger.info("Logging configuration initialized")


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(f"retargeting_service.{name}")


# Logging configuration for different environments
LOGGING_CONFIGS: Dict[str, Dict[str, Any]] = {
    "development": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    },
    "production": {
        "level": "INFO",
        "format": "%(asctime)s - %(levelname)s - %(message)s"
    },
    "testing": {
        "level": "WARNING",
        "format": "%(levelname)s - %(message)s"
    }
}