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
    max_tokens: int = int(os.getenv('OPENAI_MAX_TOKENS', '2048'))
    temperature: float = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    prompt_id: Optional[str] = os.getenv('OPENAI_PROMPT_ID')
    prompt_version: str = os.getenv('OPENAI_PROMPT_VERSION', '1')

    # Organization extraction responsive prompt configuration
    org_extract_prompt_id: Optional[str] = os.getenv('OPENAI_ORG_EXTRACT_PROMPT_ID')
    org_extract_prompt_version: str = os.getenv('OPENAI_ORG_EXTRACT_PROMPT_VERSION', '1')
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set")


@dataclass
class MessageBufferConfig:
    """Message buffering configuration settings."""
    timeout: float = float(os.getenv('MESSAGE_BUFFER_TIMEOUT', '10.0'))
    max_size: int = int(os.getenv('MESSAGE_BUFFER_MAX_SIZE', '10'))
    max_chinese_chars: int = int(os.getenv('MESSAGE_BUFFER_MAX_CHINESE_CHARS', '1000'))


@dataclass
class HandoverConfig:
    """User handover configuration settings."""
    timeout_hours: int = int(os.getenv('HANDOVER_TIMEOUT_HOURS', '1'))
    cleanup_interval_minutes: int = int(os.getenv('HANDOVER_CLEANUP_INTERVAL_MINUTES', '15'))


@dataclass
class GoogleSheetsConfig:
    """Google Sheets integration configuration settings."""
    enabled: bool = os.getenv('GOOGLE_SHEETS_ENABLED', 'False').lower() == 'true'
    credentials_path: str = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials/google-service-account.json')
    spreadsheet_id: str = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    sync_interval_minutes: int = int(os.getenv('GOOGLE_SHEETS_SYNC_INTERVAL', '10'))


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
    handover: HandoverConfig = None
    google_sheets: GoogleSheetsConfig = None
    
    def __post_init__(self):
        self.database = DatabaseConfig()
        self.line = LineConfig()
        self.openai = OpenAIConfig()
        self.message_buffer = MessageBufferConfig()
        self.handover = HandoverConfig()
        self.google_sheets = GoogleSheetsConfig()


# Global configuration instance
config = AppConfig()