"""
Custom exceptions for Dream Line Bot.
Provides specific exception types for better error handling and debugging.
"""


class DreamBotException(Exception):
    """Base exception for all Dream Bot related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(DreamBotException):
    """Raised when there's a configuration issue."""
    pass


class DatabaseError(DreamBotException):
    """Raised when database operations fail."""
    pass


class OpenAIError(DreamBotException):
    """Raised when OpenAI API calls fail."""
    pass


class LineAPIError(DreamBotException):
    """Raised when LINE API calls fail."""
    pass


class MessageProcessingError(DreamBotException):
    """Raised when message processing fails."""
    pass


class ValidationError(DreamBotException):
    """Raised when data validation fails."""
    pass


class RateLimitError(DreamBotException):
    """Raised when rate limits are exceeded."""
    pass


class TimeoutError(DreamBotException):
    """Raised when operations timeout."""
    pass