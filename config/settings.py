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
    confidence_threshold: float = float(os.getenv('AI_CONFIDENCE_THRESHOLD', '0.83'))
    
    # Agents API configuration
    model: str = os.getenv('OPENAI_MODEL', 'gpt-4')
    max_tokens: int = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
    temperature: float = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    vector_store_id: Optional[str] = os.getenv('OPENAI_VECTOR_STORE_ID')
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set")


@dataclass
class MessageBufferConfig:
    """Message buffering configuration settings."""
    timeout: float = float(os.getenv('MESSAGE_BUFFER_TIMEOUT', '10.0'))
    max_size: int = int(os.getenv('MESSAGE_BUFFER_MAX_SIZE', '10'))
    min_length: int = int(os.getenv('MESSAGE_BUFFER_MIN_LENGTH', '50'))



@dataclass
class AppConfig:
    """Main application configuration."""
    environment: str = os.getenv('ENVIRONMENT', 'development')
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    host: str = os.getenv('HOST', '0.0.0.0')
    port: int = int(os.getenv('PORT', '5000'))
    
    # AI Debug Information Switch
    show_ai_debug_info: bool = os.getenv('SHOW_AI_DEBUG_INFO', 'False').lower() == 'true'
    
    # Sub-configurations
    database: DatabaseConfig = None
    line: LineConfig = None
    openai: OpenAIConfig = None
    message_buffer: MessageBufferConfig = None
    
    def __post_init__(self):
        self.database = DatabaseConfig()
        self.line = LineConfig()
        self.openai = OpenAIConfig()
        self.message_buffer = MessageBufferConfig()


# Global configuration instance
config = AppConfig()