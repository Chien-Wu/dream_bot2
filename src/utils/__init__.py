"""Utility modules for Dream Line Bot."""
from .logger import setup_logger, log_user_action, log_error_with_context
from .exceptions import (
    DreamBotException,
    ConfigurationError,
    DatabaseError,
    OpenAIError,
    LineAPIError,
    MessageProcessingError,
    ValidationError,
    RateLimitError,
    TimeoutError
)
from .text_utils import count_chinese_characters
from .auth_decorator import require_admin_auth

__all__ = [
    'setup_logger',
    'log_user_action',
    'log_error_with_context',
    'DreamBotException',
    'ConfigurationError',
    'DatabaseError',
    'OpenAIError',
    'LineAPIError',
    'MessageProcessingError',
    'ValidationError',
    'RateLimitError',
    'TimeoutError',
    'count_chinese_characters',
    'require_admin_auth'
]