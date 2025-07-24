"""
User data models and entities.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class User:
    """User entity model."""
    user_id: str
    thread_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass 
class Message:
    """Message entity model."""
    content: str
    user_id: str
    message_type: str = "text"
    timestamp: Optional[datetime] = None
    reply_token: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AIResponse:
    """AI response model with confidence scoring."""
    text: str
    confidence: float
    user_id: str
    explanation: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
            
    @property
    def needs_human_review(self) -> bool:
        """Check if response needs human review based on confidence."""
        from config import config
        return self.confidence < config.openai.confidence_threshold