"""
Central message processor that coordinates all message handling.
"""
import time
import threading
from typing import Optional

from config import config
from src.utils import setup_logger, log_user_action, MessageProcessingError
from src.models import Message, AIResponse
from src.services import DatabaseService, AgentsAPIService, LineService
from src.services.admin_command_service import AdminCommandService
from src.services.user_handover_service import UserHandoverService
from src.core.message_buffer import message_buffer


logger = setup_logger(__name__)


class MessageProcessor:
    """Central processor for handling incoming messages."""
    
    def __init__(self,
                 database_service: DatabaseService,
                 agents_api_service: AgentsAPIService,
                 line_service: LineService,
                 admin_command_service: AdminCommandService,
                 user_handover_service: UserHandoverService):
        self.db = database_service
        self.agents_api_service = agents_api_service
        self.line = line_service
        self.admin_commands = admin_command_service
        self.handover_service = user_handover_service
        
        # Use Agents API service exclusively
        self.ai = agents_api_service
        logger.info("Using Agents API service")
        
        # Debug: Verify admin command service is properly initialized
        logger.info(f"MessageProcessor initialized with AdminCommandService: {id(self.admin_commands)}")
        try:
            logger.info(f"AdminCommandService has {len(self.admin_commands.commands)} registered commands")
        except (TypeError, AttributeError):
            # Handle mock objects in tests
            logger.info("AdminCommandService initialized (mock or missing commands)")
        
        # Set up message buffer callback
        message_buffer.set_process_callback(self._process_buffered_message)
    
    def process_message(self, message: Message) -> None:
        """
        Process an incoming message with queue management and buffering.
        
        Args:
            message: Incoming message to process
        """
        # Try to buffer the message if it's short and incomplete
        if message_buffer.add_message(message):
            logger.debug(f"Message buffered for user {message.user_id}")
            return
        
        # If not buffered, process normally
        # Start processing in background thread to avoid blocking
        threading.Thread(
            target=self._handle_single_message,
            args=(message,),
            daemon=True
        ).start()
    
    
    def _handle_single_message(self, message: Message) -> None:
        """
        Handle a single message using chain of responsibility pattern.
        
        Args:
            message: Message to process
        """
        try:
            # Check handover flag first - block AI if user is in handover mode
            if self.handover_service.is_in_handover(message.user_id):
                # Reset handover flag timer - extends expiry by another hour from now
                self.handover_service.set_handover_flag(message.user_id)
                
                log_user_action(
                    logger, 
                    message.user_id, 
                    "handover_blocked_activity_reset",
                    message_type=message.message_type,
                    content_length=len(message.content)
                )
                return  # Silent block - no messages sent
            
            log_user_action(
                logger, 
                message.user_id, 
                "message_received",
                message_type=message.message_type,
                content_length=len(message.content)
            )
            
            # Ensure user record exists in organization_data table
            self._ensure_user_record(message.user_id)

            # Chain of responsibility - each handler returns True if it handled the message
            handlers = [
                self._handle_non_text_messages,
                self._handle_admin_commands,
                self._handle_handover_requests,
                self._handle_ai_response
            ]
            
            for i, handler in enumerate(handlers):
                try:
                    handler_name = handler.__name__
                    logger.debug(f"Running handler {i+1}/5: {handler_name} for user {message.user_id}")
                    if handler(message):
                        logger.info(f"Message handled by {handler_name} for user {message.user_id}")
                        break
                    else:
                        logger.debug(f"Handler {handler_name} passed on message for user {message.user_id}")
                except Exception as handler_error:
                    logger.error(f"Handler {handler.__name__} failed for user {message.user_id}: {handler_error}")
                    # Continue to next handler instead of breaking the chain
                    continue
            else:
                # This happens if no handler processed the message
                logger.warning(f"No handler processed message for user {message.user_id}: '{message.content[:50]}...'")
                    
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
            
            # Use the same handler chain
            self._handle_single_message(virtual_message)
            
        except Exception as e:
            logger.error(f"Failed to process buffered message for user {user_id}: {e}")
            self._send_error_response(user_id, reply_token)
    
    def _handle_non_text_messages(self, message: Message) -> bool:
        """Handle non-text messages (images, stickers, etc.)."""
        if message.message_type == "image":
            try:
                self.line.notify_admin(
                    user_id=message.user_id,
                    user_msg="使用者傳送了一張圖片",
                    notification_type="image"
                )
                
                self.line.send_message(
                    message.user_id,
                    "已為您通知管理者，請稍候。",
                    message.reply_token
                )
                return True
                
            except Exception as e:
                logger.error(f"Failed to handle image message: {e}")
                return True
        
        if message.message_type != "text":
            logger.debug(f"Ignoring message type: {message.message_type}")
            return True
            
        return False
    
    def _handle_admin_commands(self, message: Message) -> bool:
        """Handle admin commands."""
        if not self._is_admin_user(message.user_id):
            return False
        
        if not self.admin_commands.is_admin_command(message.content):
            return False
            
        try:
            logger.info(f"Processing admin command from {message.user_id}: {message.content}")
            
            log_user_action(
                logger,
                message.user_id,
                "admin_command_received",
                command=message.content
            )
            
            response = self.admin_commands.execute_command(message.content)
            
            self.line.send_raw_message(
                message.user_id,
                response,
                message.reply_token
            )
            
            log_user_action(
                logger,
                message.user_id,
                "admin_command_executed",
                command=message.content.split()[0] if message.content.split() else "",
                success=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle admin command from {message.user_id}: {e}")
            self.line.send_raw_message(
                message.user_id,
                "❌ 執行管理指令時發生錯誤，請稍後再試。",
                message.reply_token
            )
            return True
    
    def _ensure_user_record(self, user_id: str) -> None:
        """Ensure user record exists in organization_data table."""
        try:
            self.db.ensure_user_record(user_id)
        except Exception as e:
            logger.error(f"Failed to ensure user record for {user_id}: {e}")
    
    def _handle_handover_requests(self, message: Message) -> bool:
        """Handle requests for human handover."""
        if not self.line.is_handover_request(message.content):
            return False
            
        try:
            # Set handover flag first
            self.handover_service.set_handover_flag(message.user_id)
            
            self.line.notify_admin(
                user_id=message.user_id,
                user_msg=message.content,
                notification_type="handover"
            )
            
            self.line.send_message(
                message.user_id,
                "已為您通知管理者，請稍候。",
                message.reply_token
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle handover request: {e}")
            return True
    
    def _handle_ai_response(self, message: Message) -> bool:
        """Handle AI response generation and sending."""
        try:
            logger.debug(f"Getting AI response for user {message.user_id}")
            
            # Get AI response
            ai_response = self.ai.get_response(message.user_id, message.content)
            
            logger.debug(f"AI response received for user {message.user_id}: confidence={ai_response.confidence:.2f}, needs_review={ai_response.needs_human_review}")
            
            # Send normal response first
            if ai_response.needs_human_review:
                logger.info(f"Low confidence AI response for user {message.user_id}, setting handover flag")
                
                # Set handover flag for low confidence responses
                self.handover_service.set_handover_flag(message.user_id)
                
                # Notify admin for low confidence responses
                try:
                    # Extract first query "q" field if available
                    ai_query = None
                    if ai_response.queries and len(ai_response.queries) > 0:
                        first_query = ai_response.queries[0]
                        if isinstance(first_query, dict) and "q" in first_query:
                            ai_query = first_query["q"]
                    
                    self.line.notify_admin(
                        user_id=message.user_id,
                        user_msg=message.content,
                        confidence=ai_response.confidence,
                        ai_explanation=ai_response.explanation,
                        notification_type="low_confidence",
                        ai_query=ai_query
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")
                
                # Low confidence - send handover message
                handover_message = "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！"
                logger.debug(f"Sending handover message to user {message.user_id}")
                self.line.send_message(message.user_id, handover_message, message.reply_token)
            else:
                # High confidence - send AI response
                logger.debug(f"Sending high confidence AI response to user {message.user_id}")
                self.line.send_message(message.user_id, ai_response.text, message.reply_token)
            
            # Push debug info separately if enabled
            if config.show_ai_debug_info:
                debug_info = "🔧 AI詳細資訊：\n"
                if ai_response.explanation:
                    debug_info += f"AI說明：\n{ai_response.explanation}\n"
                debug_info += f"信心度：{ai_response.confidence:.2f}"
                
                # Push debug info as separate message
                time.sleep(0.5)  # Small delay to ensure proper message order
                self.line.push_message(message.user_id, debug_info)
            
            log_user_action(
                logger,
                message.user_id,
                "message_processed",
                confidence=ai_response.confidence,
                needs_review=ai_response.needs_human_review
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to get AI response for user {message.user_id}: {e}")
            import traceback
            logger.error(f"AI response error traceback: {traceback.format_exc()}")
            self._send_error_response(message.user_id, message.reply_token)
            return True
    
    def _is_admin_user(self, user_id: str) -> bool:
        """Check if user is an admin."""
        is_admin = user_id == config.line.admin_user_id
        logger.debug(f"Admin check: user_id={user_id}, admin_user_id={config.line.admin_user_id}, is_admin={is_admin}")
        return is_admin
    
    
    def _send_error_response(self, user_id: str, reply_token: str = None) -> None:
        """Send error response to user."""
        try:
            error_response = "系統處理您的訊息時發生錯誤，請稍後再試。"
            self.line.send_message(user_id, error_response, reply_token)
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")
    
    def _handle_processing_error(self, message: Message, error: Exception) -> None:
        """Handle errors during message processing."""
        self._send_error_response(message.user_id, message.reply_token)
        
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