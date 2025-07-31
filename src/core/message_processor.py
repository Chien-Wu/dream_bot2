"""
Central message processor that coordinates all message handling.
"""
import time
import threading
from typing import Optional

from config import config
from src.utils import setup_logger, log_user_action, MessageProcessingError
from src.models import Message, AIResponse
from src.services import DatabaseService, OpenAIService, LineService
from src.services.welcome_flow_manager import WelcomeFlowManager
from src.services.admin_command_service import AdminCommandService
from src.core.message_buffer import message_buffer


logger = setup_logger(__name__)


class MessageProcessor:
    """Central processor for handling incoming messages."""
    
    def __init__(self, 
                 database_service: DatabaseService,
                 openai_service: OpenAIService, 
                 line_service: LineService,
                 welcome_flow_manager: WelcomeFlowManager,
                 admin_command_service: AdminCommandService):
        self.db = database_service
        self.ai = openai_service
        self.line = line_service
        self.welcome_flow = welcome_flow_manager
        self.admin_commands = admin_command_service
        
        # Debug: Verify admin command service is properly initialized
        logger.info(f"MessageProcessor initialized with AdminCommandService: {id(self.admin_commands)}")
        logger.info(f"AdminCommandService has {len(self.admin_commands.commands)} registered commands")
        
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
            
            # Check if this is an admin command
            is_admin = self._is_admin_user(message.user_id)
            is_command = self.admin_commands.is_admin_command(message.content)
            
            logger.debug(f"Admin check - user_id: {message.user_id}, is_admin: {is_admin}, is_command: {is_command}, content: {message.content[:50]}")
            
            if is_admin and is_command:
                logger.info(f"Processing admin command from {message.user_id}: {message.content}")
                self._handle_admin_command(message)
                return
            
            # Check welcome flow (organization data collection)
            welcome_result = self.welcome_flow.process_message(message.user_id, message.content)
            
            if welcome_result.should_block:
                # Send response message if provided
                if welcome_result.response_message and message.reply_token:
                    self.line.reply_message_to_user(
                        message.reply_token, 
                        message.user_id, 
                        welcome_result.response_message
                    )
                
                # Notify admin if needed
                if welcome_result.notify_admin and welcome_result.admin_message:
                    self.line.notify_admin(
                        user_id=message.user_id,
                        user_msg=welcome_result.admin_message,
                        notification_type="org_complete"
                    )
                
                # Update user context in ChatGPT if organization data is complete
                if welcome_result.context_updated:
                    try:
                        # Get existing thread to update context
                        thread_id = self.db.get_user_thread_id(message.user_id)
                        if thread_id:
                            self.ai._refresh_user_context(message.user_id, thread_id)
                    except Exception as e:
                        logger.error(f"Failed to update user context for {message.user_id}: {e}")
                
                # Block further processing
                return
            
            # Check for handover request
            if self.line.is_handover_request(message.content):
                self._handle_handover_request(message)
                return
            
            
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
            
            # Check welcome flow first (organization data collection)
            welcome_result = self.welcome_flow.process_message(user_id, combined_content)
            
            if welcome_result.should_block:
                # Send response message if provided
                if welcome_result.response_message:
                    if reply_token:
                        self.line.reply_message_to_user(reply_token, user_id, welcome_result.response_message)
                    else:
                        self.line.push_message_with_split(user_id, welcome_result.response_message)
                
                # Notify admin if needed
                if welcome_result.notify_admin and welcome_result.admin_message:
                    self.line.notify_admin(
                        user_id=user_id,
                        user_msg=welcome_result.admin_message,
                        notification_type="org_complete"
                    )
                
                # Update user context in ChatGPT if organization data is complete
                if welcome_result.context_updated:
                    try:
                        # Get existing thread to update context
                        thread_id = self.db.get_user_thread_id(user_id)
                        if thread_id:
                            self.ai._refresh_user_context(user_id, thread_id)
                    except Exception as e:
                        logger.error(f"Failed to update user context for {user_id}: {e}")
                
                # Block further processing
                return
            
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
    
    def _handle_image_message(self, message: Message) -> None:
        """Handle image messages by notifying admin."""
        try:
            self.line.notify_admin(
                user_id=message.user_id,
                user_msg="使用者傳送了一張圖片",
                ai_reply="系統自動通知，請人工介入處理",
                notification_type="image"
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
                user_msg=message.content,
                notification_type="handover"
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
                    confidence=ai_response.confidence,
                    ai_explanation=ai_response.explanation,
                    notification_type="low_confidence"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")
            
            # For low confidence: show debug info if switch is on
            if config.show_ai_debug_info:
                debug_response = "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！\n\n"
                debug_response += "🔧 AI詳細資訊：\n"
                debug_response += f"AI回覆：{ai_response.text}\n"
                if ai_response.explanation:
                    debug_response += f"AI說明：{ai_response.explanation}\n"
                debug_response += f"信心度：{ai_response.confidence:.2f}"
                return debug_response
            else:
                return "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！"
        
        # For high confidence: build response based on debug switch
        response_parts = [ai_response.text]
        
        if config.show_ai_debug_info:
            # Show explanation and confidence when debug switch is on
            if ai_response.explanation:
                response_parts.append(f"\n\n📋 詳細說明：\n{ai_response.explanation}")
            response_parts.append(f"\n\n🔧 信心度：{ai_response.confidence:.2f}")
        
        return "".join(response_parts)
    
    def _is_admin_user(self, user_id: str) -> bool:
        """Check if user is an admin."""
        is_admin = user_id == config.line.admin_user_id
        logger.debug(f"Admin check: user_id={user_id}, admin_user_id={config.line.admin_user_id}, is_admin={is_admin}")
        return is_admin
    
    def _handle_admin_command(self, message: Message) -> None:
        """Handle admin command execution."""
        try:
            log_user_action(
                logger,
                message.user_id,
                "admin_command_received",
                command=message.content
            )
            
            # Parse and execute command
            command, args = self.admin_commands.parse_command(message.content)
            result = self.admin_commands.execute_command(command, args)
            
            # Send response
            if message.reply_token:
                self.line.reply_message_to_user(
                    message.reply_token,
                    message.user_id,
                    result.message
                )
                
            log_user_action(
                logger,
                message.user_id,
                "admin_command_executed",
                command=command,
                success=result.success
            )
            
        except Exception as e:
            logger.error(f"Failed to handle admin command from {message.user_id}: {e}")
            
            # Send error response
            try:
                error_message = "❌ 執行管理指令時發生錯誤，請稍後再試。"
                if message.reply_token:
                    self.line.reply_message_to_user(
                        message.reply_token,
                        message.user_id,
                        error_message
                    )
            except Exception as error_send_error:
                logger.error(f"Failed to send admin command error response: {error_send_error}")
    
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