"""
Tests for MessageProcessor class.
"""
import pytest
from unittest.mock import Mock, patch

from src.core.message_processor import MessageProcessor
from src.models import Message, AIResponse


class TestMessageProcessor:
    """Test cases for MessageProcessor."""
    
    def test_process_text_message_high_confidence(
        self, 
        message_processor, 
        sample_text_message,
        sample_ai_response,
        mock_openai_service,
        mock_line_service
    ):
        """Test processing text message with high confidence AI response."""
        # Setup
        mock_openai_service.get_response.return_value = sample_ai_response
        
        # Execute
        message_processor.process_message(sample_text_message)
        
        # Verify
        mock_openai_service.get_response.assert_called_once_with(
            sample_text_message.user_id, 
            sample_text_message.content
        )
        mock_line_service.reply_message.assert_called_once_with(
            sample_text_message.reply_token,
            sample_ai_response.text
        )
        mock_line_service.notify_admin.assert_not_called()
    
    def test_process_text_message_low_confidence(
        self,
        message_processor,
        sample_text_message, 
        low_confidence_ai_response,
        mock_openai_service,
        mock_line_service
    ):
        """Test processing text message with low confidence AI response."""
        # Setup
        mock_openai_service.get_response.return_value = low_confidence_ai_response
        
        # Execute
        message_processor.process_message(sample_text_message)
        
        # Verify
        mock_line_service.notify_admin.assert_called_once_with(
            user_id=sample_text_message.user_id,
            user_msg=sample_text_message.content,
            ai_reply=low_confidence_ai_response.text,
            confidence=low_confidence_ai_response.confidence
        )
        mock_line_service.reply_message.assert_called_once_with(
            sample_text_message.reply_token,
            "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！"
        )
    
    def test_process_image_message(
        self,
        message_processor,
        sample_image_message,
        mock_line_service
    ):
        """Test processing image message."""
        # Execute
        message_processor.process_message(sample_image_message)
        
        # Verify
        mock_line_service.notify_admin.assert_called_once_with(
            user_id=sample_image_message.user_id,
            user_msg="使用者傳送了一張圖片",
            ai_reply="系統自動通知，請人工介入處理"
        )
        mock_line_service.reply_message.assert_called_once_with(
            sample_image_message.reply_token,
            "已為您通知管理者，請稍候。"
        )
    
    def test_process_handover_request(
        self,
        message_processor,
        mock_line_service
    ):
        """Test processing handover request message."""
        # Setup
        handover_message = Message(
            content="轉人工",
            user_id="test_user",
            message_type="text",
            reply_token="test_token"
        )
        mock_line_service.is_handover_request.return_value = True
        
        # Execute
        message_processor.process_message(handover_message)
        
        # Verify
        mock_line_service.notify_admin.assert_called_once_with(
            user_id=handover_message.user_id,
            user_msg=handover_message.content
        )
        mock_line_service.reply_message.assert_called_once_with(
            handover_message.reply_token,
            "已為您通知管理者，請稍候。"
        )
    
    def test_process_message_error_handling(
        self,
        message_processor,
        sample_text_message,
        mock_openai_service,
        mock_line_service
    ):
        """Test error handling during message processing."""
        # Setup
        mock_openai_service.get_response.side_effect = Exception("OpenAI Error")
        
        # Execute
        message_processor.process_message(sample_text_message)
        
        # Verify error response is sent
        mock_line_service.reply_message.assert_called_once_with(
            sample_text_message.reply_token,
            "系統發生錯誤，請稍後再試。"
        )