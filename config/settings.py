"""
Configuration management for Dream Line Bot.
Centralizes all environment variables and application settings.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = os.getenv('MYSQL_HOST', 'localhost')
    user: str = os.getenv('MYSQL_USER', 'root')
    password: Optional[str] = os.getenv('MYSQL_PASSWORD')
    database: Optional[str] = os.getenv('MYSQL_DATABASE')
    charset: str = 'utf8mb4'
    
    def __post_init__(self):
        if not self.database:
            raise ValueError("MYSQL_DATABASE must be set")


@dataclass
class LineConfig:
    """LINE Bot configuration settings."""
    channel_access_token: Optional[str] = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    channel_secret: Optional[str] = os.getenv('LINE_CHANNEL_SECRET')
    admin_user_id: Optional[str] = os.getenv('LINE_ADMIN_USER_ID')
    
    def __post_init__(self):
        if not self.channel_access_token or not self.channel_secret:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET must be set")


@dataclass
class OpenAIConfig:
    """OpenAI API configuration settings."""
    api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
    assistant_id: Optional[str] = os.getenv('OPENAI_ASSISTANT_ID')
    max_poll_retries: int = int(os.getenv('OPENAI_POLL_MAX_RETRIES', '30'))
    poll_interval: float = float(os.getenv('OPENAI_POLL_INTERVAL', '1.0'))
    confidence_threshold: float = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.83'))
    
    def __post_init__(self):
        if not self.api_key or not self.assistant_id:
            raise ValueError("OPENAI_API_KEY and OPENAI_ASSISTANT_ID must be set")


@dataclass
class AppConfig:
    """Main application configuration."""
    environment: str = os.getenv('ENVIRONMENT', 'development')
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    host: str = os.getenv('HOST', '0.0.0.0')
    port: int = int(os.getenv('PORT', '5000'))
    
    # Sub-configurations
    database: DatabaseConfig = None
    line: LineConfig = None
    openai: OpenAIConfig = None
    
    def __post_init__(self):
        self.database = DatabaseConfig()
        self.line = LineConfig()
        self.openai = OpenAIConfig()


# Global configuration instance
config = AppConfig()