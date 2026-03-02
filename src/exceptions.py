"""
Custom exceptions for the Real-Time Retargeting & Optimization Signals Service
"""


class RetargetingServiceError(Exception):
    """Base exception for all retargeting service errors"""
    pass


class StorageError(RetargetingServiceError):
    """Raised when storage operations fail"""
    pass


class RedisConnectionError(StorageError):
    """Raised when Redis connection fails"""
    pass


class UserProfileNotFoundError(RetargetingServiceError):
    """Raised when a user profile cannot be found"""
    pass


class InvalidEventError(RetargetingServiceError):
    """Raised when an event is invalid or malformed"""
    pass


class ProcessingError(RetargetingServiceError):
    """Raised when event processing fails"""
    pass


class AudienceError(RetargetingServiceError):
    """Raised when audience operations fail"""
    pass


class ConfigurationError(RetargetingServiceError):
    """Raised when configuration is invalid"""
    pass