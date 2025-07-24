"""
Test configuration and fixtures for Dream Line Bot.
"""
import pytest
from unittest.mock import Mock, MagicMock
import os

# Set test environment
os.environ.update({
    'ENVIRONMENT': 'test',
    'MYSQL_HOST': 'localhost',
    'MYSQL_USER': 'test_user',
    'MYSQL_PASSWORD': 'test_password',
    'MYSQL_DATABASE': 'test_db',
    'LINE_CHANNEL_ACCESS_TOKEN': 'test_line_token',
    'LINE_CHANNEL_SECRET': 'test_line_secret',
    'OPENAI_API_KEY': 'test_openai_key',
    'OPENAI_ASSISTANT_ID': 'test_assistant_id',
    'LOG_LEVEL': 'DEBUG'
})

from src.models import User, Message, AIResponse
from src.services import DatabaseService, OpenAIService, LineService
from src.core import MessageProcessor


@pytest.fixture
def mock_database_service():
    """Mock database service for testing."""
    mock_db = Mock(spec=DatabaseService)
    mock_db.get_user_thread_id.return_value = "test_thread_id"
    mock_db.set_user_thread_id.return_value = None
    mock_db.reset_user_thread.return_value = None
    mock_db.log_message.return_value = None
    return mock_db


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service for testing."""
    mock_ai = Mock(spec=OpenAIService)
    mock_ai.get_response.return_value = AIResponse(
        text="Test AI response",
        confidence=0.95,
        explanation=None,
        user_id="test_user"
    )
    return mock_ai


@pytest.fixture
def mock_line_service():
    """Mock LINE service for testing."""
    mock_line = Mock(spec=LineService)
    mock_line.reply_message.return_value = None
    mock_line.push_message.return_value = None
    mock_line.notify_admin.return_value = None
    mock_line.is_handover_request.return_value = False
    return mock_line


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(user_id="test_user_123")


@pytest.fixture
def sample_text_message():
    """Sample text message for testing."""
    return Message(
        content="Hello, this is a test message",
        user_id="test_user_123",
        message_type="text",
        reply_token="test_reply_token"
    )


@pytest.fixture
def sample_image_message():
    """Sample image message for testing."""
    return Message(
        content="[Image]",
        user_id="test_user_123", 
        message_type="image",
        reply_token="test_reply_token"
    )


@pytest.fixture
def sample_ai_response():
    """Sample AI response for testing."""
    return AIResponse(
        text="This is a test AI response",
        confidence=0.95,
        explanation=None,
        user_id="test_user_123"
    )


@pytest.fixture
def low_confidence_ai_response():
    """Sample low confidence AI response for testing."""
    return AIResponse(
        text="This is a low confidence response",
        confidence=0.50,
        explanation=None,
        user_id="test_user_123"
    )


@pytest.fixture
def message_processor(mock_database_service, mock_openai_service, mock_line_service):
    """Message processor with mocked dependencies."""
    return MessageProcessor(
        database_service=mock_database_service,
        openai_service=mock_openai_service,
        line_service=mock_line_service
    )