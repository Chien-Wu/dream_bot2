"""
Centralized logging configuration for Dream Line Bot.
Provides structured logging with different handlers for development and production.
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from config import config


class CustomFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        if hasattr(record, 'user_id'):
            record.msg = f"[User:{record.user_id}] {record.msg}"
            
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    log_level = getattr(logging, (level or config.log_level).upper())
    logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if config.environment == 'development':
        console_formatter = CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for production
    if config.environment == 'production':
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'dream_bot.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_user_action(logger: logging.Logger, user_id: str, action: str, **kwargs):
    """Log user actions with structured data."""
    extra_data = {'user_id': user_id}
    extra_data.update(kwargs)
    logger.info(f"User action: {action}", extra=extra_data)


def log_error_with_context(logger: logging.Logger, error: Exception, context: dict = None):
    """Log errors with additional context."""
    context = context or {}
    logger.error(
        f"Error occurred: {type(error).__name__}: {error}",
        extra=context,
        exc_info=True
    )