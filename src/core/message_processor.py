"""
Central message processor that coordinates all message handling.
"""
import time
import threading
from typing import Optional

from src.utils import setup_logger, log_user_action, MessageProcessingError
from src.models import Message, AIResponse
from src.services import DatabaseService, OpenAIService, LineService
from src.core.message_queue import message_queue
from src.core.message_buffer import message_buffer


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
        
        # Set up message buffer callback
        message_buffer.set_process_callback(self._process_buffered_message)
    
    def process_message(self, message: Message) -> None:
        """
        Process an incoming message with queue management and buffering.
        
        Args:
            message: Incoming message to process
        """
        # Add message to queue for rate limiting and duplicate detection
        if not message_queue.add_message(message):
            logger.debug(f"Message rejected by queue for user {message.user_id}")
            return
        
        # Try to buffer the message if it's short and incomplete
        if message_buffer.add_message(message):
            logger.debug(f"Message buffered for user {message.user_id}")
            return
        
        # If not buffered, process normally
        # Start processing in background thread to avoid blocking
        threading.Thread(
            target=self._process_user_messages,
            args=(message.user_id,),
            daemon=True
        ).start()
    
    def _process_user_messages(self, user_id: str) -> None:
        """
        Process all queued messages for a user sequentially.
        
        Args:
            user_id: User ID to process messages for
        """
        # Check if already processing for this user
        if message_queue.is_user_processing(user_id):
            logger.debug(f"Already processing messages for user {user_id}")
            return
        
        message_queue.set_user_processing(user_id, True)
        
        try:
            while True:
                # Get next message from queue
                message = message_queue.get_next_message(user_id)
                if not message:
                    break
                
                # Process the message
                self._handle_single_message(message)
                
                # Add small delay between processing messages
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error processing messages for user {user_id}: {e}")
        finally:
            message_queue.set_user_processing(user_id, False)
    
    def _handle_single_message(self, message: Message) -> None:
        """
        Handle a single message (core processing logic).
        
        Args:
            message: Message to process
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
            
            # Check queue size - if multiple messages queued, send acknowledgment
            queue_size = message_queue.get_queue_size(message.user_id)
            if queue_size > 1:
                self._send_queue_acknowledgment(message, queue_size)
            
            # Get AI response
            ai_response = self.ai.get_response(message.user_id, message.content)
            
            # Determine final response based on confidence
            final_text = self._determine_final_response(message, ai_response)
            
            # Send reply (split by Chinese periods if needed)
            if message.reply_token:
                self.line.reply_message_to_user(message.reply_token, message.user_id, final_text)
            
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
    
    def _process_buffered_message(self, user_id: str, combined_content: str, reply_token: str) -> None:
        """
        Process a buffered message that was combined from multiple short messages.
        
        Args:
            user_id: User ID
            combined_content: Combined message content
            reply_token: Reply token from the last message
        """
        try:
            log_user_action(
                logger,
                user_id,
                "buffered_message_processed",
                content_length=len(combined_content)
            )
            
            # Create a virtual message for processing
            virtual_message = Message(
                content=combined_content,
                user_id=user_id,
                message_type="text",
                reply_token=reply_token
            )
            
            # Check for handover request in combined content
            if self.line.is_handover_request(combined_content):
                self._handle_handover_request(virtual_message)
                return
            
            # Get AI response for combined content
            ai_response = self.ai.get_response(user_id, combined_content)
            
            # Determine final response
            final_text = self._determine_final_response(virtual_message, ai_response)
            
            # Send reply
            if reply_token:
                self.line.reply_message_to_user(reply_token, user_id, final_text)
            else:
                # If no reply token, send as push message
                self.line.push_message_with_split(user_id, final_text)
            
            log_user_action(
                logger,
                user_id,
                "buffered_message_completed",
                confidence=ai_response.confidence,
                needs_review=ai_response.needs_human_review
            )
            
        except Exception as e:
            logger.error(f"Failed to process buffered message for user {user_id}: {e}")
            
            # Send error response
            try:
                error_response = "系統處理您的訊息時發生錯誤，請稍後再試。"
                if reply_token:
                    self.line.reply_message_to_user(reply_token, user_id, error_response)
                else:
                    self.line.push_message(user_id, error_response)
            except Exception as error_send_error:
                logger.error(f"Failed to send error response: {error_send_error}")
    
    def _send_queue_acknowledgment(self, message: Message, queue_size: int) -> None:
        """
        Send acknowledgment for queued messages.
        
        Args:
            message: Current message being processed
            queue_size: Number of messages in queue
        """
        try:
            if queue_size <= 1:
                return
                
            ack_message = f"收到您的訊息，目前有 {queue_size} 條訊息待處理，請稍候。"
            
            # Send as push message to avoid using reply token
            self.line.push_message(message.user_id, ack_message)
            
            logger.info(f"Sent queue acknowledgment to user {message.user_id} (queue size: {queue_size})")
            
        except Exception as e:
            logger.error(f"Failed to send queue acknowledgment: {e}")
    
    def _handle_image_message(self, message: Message) -> None:
        """Handle image messages by notifying admin."""
        try:
            self.line.notify_admin(
                user_id=message.user_id,
                user_msg="使用者傳送了一張圖片",
                ai_reply="系統自動通知，請人工介入處理"
            )
            
            if message.reply_token:
                self.line.reply_message_to_user(
                    message.reply_token,
                    message.user_id,
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
                self.line.reply_message_to_user(
                    message.reply_token,
                    message.user_id,
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
                self.line.reply_message_to_user(message.reply_token, message.user_id, error_response)
                
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