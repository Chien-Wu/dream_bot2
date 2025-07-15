"""
Central message processor that coordinates all message handling.
"""
from typing import Optional

from src.utils import setup_logger, log_user_action, MessageProcessingError
from src.models import Message, AIResponse
from src.services import DatabaseService, OpenAIService, LineService


logger = setup_logger(__name__)


class MessageProcessor:
    """Central processor for handling incoming messages."""
    
    def __init__(self, 
                 database_service: DatabaseService,
                 openai_service: OpenAIService, 
                 line_service: LineService):
        self.db = database_service
        self.ai = openai_service
        self.line = line_service
    
    def process_message(self, message: Message) -> None:
        """
        Process an incoming message and generate appropriate response.
        
        Args:
            message: Incoming message to process
        """
        try:
            log_user_action(
                logger, 
                message.user_id, 
                f"message_received",
                message_type=message.message_type,
                content_length=len(message.content)
            )
            
            # Handle different message types
            if message.message_type == "image":
                self._handle_image_message(message)
                return
            
            if message.message_type != "text":
                logger.debug(f"Ignoring message type: {message.message_type}")
                return
            
            # Check for handover request
            if self.line.is_handover_request(message.content):
                self._handle_handover_request(message)
                return
            
            # Get AI response
            ai_response = self.ai.get_response(message.user_id, message.content)
            
            # Determine final response based on confidence
            final_text = self._determine_final_response(message, ai_response)
            
            # Send reply
            if message.reply_token:
                self.line.reply_message(message.reply_token, final_text)
            
            log_user_action(
                logger,
                message.user_id,
                "message_processed",
                confidence=ai_response.confidence,
                needs_review=ai_response.needs_human_review
            )
            
        except Exception as e:
            logger.error(f"Failed to process message from {message.user_id}: {e}")
            self._handle_processing_error(message, e)
    
    def _handle_image_message(self, message: Message) -> None:
        """Handle image messages by notifying admin."""
        try:
            self.line.notify_admin(
                user_id=message.user_id,
                user_msg="使用者傳送了一張圖片",
                ai_reply="系統自動通知，請人工介入處理"
            )
            
            if message.reply_token:
                self.line.reply_message(
                    message.reply_token,
                    "已為您通知管理者，請稍候。"
                )
                
        except Exception as e:
            logger.error(f"Failed to handle image message: {e}")
    
    def _handle_handover_request(self, message: Message) -> None:
        """Handle requests for human handover."""
        try:
            self.line.notify_admin(
                user_id=message.user_id,
                user_msg=message.content
            )
            
            if message.reply_token:
                self.line.reply_message(
                    message.reply_token,
                    "已為您通知管理者，請稍候。"
                )
                
        except Exception as e:
            logger.error(f"Failed to handle handover request: {e}")
    
    def _determine_final_response(self, message: Message, ai_response: AIResponse) -> str:
        """
        Determine final response based on AI confidence.
        
        Args:
            message: Original user message
            ai_response: AI response with confidence
            
        Returns:
            Final response text to send to user
        """
        if ai_response.needs_human_review:
            # Notify admin for low confidence responses
            try:
                self.line.notify_admin(
                    user_id=message.user_id,
                    user_msg=message.content,
                    ai_reply=ai_response.text,
                    confidence=ai_response.confidence
                )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")
            
            return "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！"
        
        # Add confidence indicator in development mode
        from config import config
        if config.environment == 'development':
            return f"{ai_response.text} (confidence: {ai_response.confidence:.2f})"
        
        return ai_response.text
    
    def _handle_processing_error(self, message: Message, error: Exception) -> None:
        """Handle errors during message processing."""
        try:
            error_response = "系統發生錯誤，請稍後再試。"
            
            if message.reply_token:
                self.line.reply_message(message.reply_token, error_response)
                
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
        
        # Log the error with context
        from src.utils import log_error_with_context
        log_error_with_context(
            logger, 
            error,
            {
                'user_id': message.user_id,
                'message_type': message.message_type,
                'content_length': len(message.content)
            }
        )