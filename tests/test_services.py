"""
Tests for service layer classes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.line_service import LineService
from src.models import Message


class TestLineService:
    """Test cases for LineService."""
    
    @patch('src.services.line_service.MessagingApi')
    @patch('src.services.line_service.Configuration')
    def test_reply_message(self, mock_config, mock_messaging_api):
        """Test replying to a message."""
        # Setup
        mock_api_instance = Mock()
        mock_messaging_api.return_value = mock_api_instance
        
        line_service = LineService()
        
        # Execute
        line_service.reply_message("test_token", "Test reply")
        
        # Verify
        mock_api_instance.reply_message.assert_called_once()
    
    @patch('src.services.line_service.MessagingApi')
    @patch('src.services.line_service.Configuration')
    def test_push_message(self, mock_config, mock_messaging_api):
        """Test pushing a message to user.""" 
        # Setup
        mock_api_instance = Mock()
        mock_messaging_api.return_value = mock_api_instance
        
        line_service = LineService()
        
        # Execute
        line_service.push_message("test_user_id", "Test push")
        
        # Verify
        mock_api_instance.push_message.assert_called_once()
    
    def test_is_handover_request(self):
        """Test handover request detection."""
        line_service = LineService()
        
        # Test positive cases
        assert line_service.is_handover_request("轉人工")
        assert line_service.is_handover_request("我要人工客服")
        assert line_service.is_handover_request("需要真人協助")
        
        # Test negative cases
        assert not line_service.is_handover_request("Hello")
        assert not line_service.is_handover_request("普通問題")
    
    def test_extract_message_text(self):
        """Test extracting text message from LINE event."""
        # Setup
        mock_event = Mock()
        mock_event.source.user_id = "test_user"
        mock_event.reply_token = "test_token"
        mock_event.message.text = "Test message"
        mock_event.message.__class__.__name__ = "TextMessageContent"
        
        # Mock hasattr to return False for group/room
        with patch('builtins.hasattr', side_effect=lambda obj, attr: False):
            line_service = LineService()
            message = line_service.extract_message(mock_event)
        
        # Verify
        assert message is not None
        assert message.content == "Test message"
        assert message.user_id == "test_user"
        assert message.message_type == "text"
        assert message.reply_token == "test_token"
    
    def test_extract_message_image(self):
        """Test extracting image message from LINE event."""
        # Setup
        mock_event = Mock()
        mock_event.source.user_id = "test_user"
        mock_event.reply_token = "test_token"
        mock_event.message.__class__.__name__ = "ImageMessageContent"
        
        # Mock hasattr to return False for group/room
        with patch('builtins.hasattr', side_effect=lambda obj, attr: False):
            line_service = LineService()
            message = line_service.extract_message(mock_event)
        
        # Verify
        assert message is not None
        assert message.content == "[Image]"
        assert message.message_type == "image"
    
    def test_extract_message_group_ignored(self):
        """Test that group messages are ignored."""
        # Setup
        mock_event = Mock()
        mock_event.source.group_id = "group123"
        
        # Mock hasattr to return True for group_id
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'group_id'):
            line_service = LineService()
            message = line_service.extract_message(mock_event)
        
        # Verify
        assert message is None