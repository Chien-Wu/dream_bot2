"""
OpenAI service for handling AI assistant interactions.
"""
import time
from typing import Optional

import openai

from config import config
from src.utils import setup_logger, OpenAIError, TimeoutError
from src.models import AIResponse
from src.services.database_service import DatabaseService


logger = setup_logger(__name__)


class OpenAIService:
    """Service for OpenAI Assistant API interactions."""
    
    def __init__(self, database_service: DatabaseService):
        self.config = config.openai
        self.db = database_service
        openai.api_key = self.config.api_key
        
    def _get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create new one for user."""
        thread_id = self.db.get_user_thread_id(user_id)
        
        if thread_id:
            logger.debug(f"Found existing thread for user {user_id}: {thread_id}")
            return thread_id
            
        logger.info(f"Creating new thread for user {user_id}")
        try:
            # Get user context for initial thread setup
            user_context = self._get_user_context(user_id)
            
            # Create thread with user context
            thread = openai.beta.threads.create()
            
            # Add user context as first message if available
            if user_context:
                openai.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"我的基本資料：\n{user_context}"
                )
            
            self.db.set_user_thread_id(user_id, thread.id)
            return thread.id
        except Exception as e:
            logger.error(f"Failed to create thread for user {user_id}: {e}")
            raise OpenAIError(f"Thread creation failed: {e}")
    
    def _send_message(self, thread_id: str, content: str) -> None:
        """Send user message to thread."""
        try:
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )
        except Exception as e:
            logger.error(f"Failed to send message to thread {thread_id}: {e}")
            raise OpenAIError(f"Message sending failed: {e}")
    
    def _start_run(self, thread_id: str) -> str:
        """Start assistant run on thread."""
        try:
            run = openai.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.config.assistant_id
            )
            return run.id
        except Exception as e:
            logger.error(f"Failed to start run on thread {thread_id}: {e}")
            raise OpenAIError(f"Run start failed: {e}")
    
    def _wait_for_completion(self, thread_id: str, run_id: str) -> bool:
        """Wait for run completion with timeout."""
        for attempt in range(self.config.max_poll_retries):
            try:
                run_status = openai.beta.threads.runs.retrieve(
                    thread_id=thread_id, 
                    run_id=run_id
                )
                
                if run_status.status == "completed":
                    return True
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Run {run_id} failed with status: {run_status.status}")
                    return False
                    
                time.sleep(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"Error checking run status: {e}")
                time.sleep(self.config.poll_interval)
        
        logger.warning(f"Run {run_id} timed out after {self.config.max_poll_retries} attempts")
        return False
    
    def _get_latest_response(self, thread_id: str) -> Optional[str]:
        """Get the latest assistant response from thread."""
        try:
            messages = openai.beta.threads.messages.list(thread_id=thread_id).data
            assistant_messages = [m for m in messages if m.role == "assistant"]
            
            if not assistant_messages:
                logger.error("No assistant messages found in thread")
                return None
                
            latest_message = assistant_messages[0]
            
            if (latest_message.content and 
                hasattr(latest_message.content[0], "text") and
                hasattr(latest_message.content[0].text, "value")):
                return latest_message.content[0].text.value
                
            logger.error("Assistant message format unexpected")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get latest response: {e}")
            return None
    
    def get_response(self, user_id: str, user_input: str) -> AIResponse:
        """
        Get AI response for user input.
        
        Args:
            user_id: User identifier
            user_input: User's message content
            
        Returns:
            AIResponse object with text and confidence
        """
        try:
            # Get or create thread
            thread_id = self._get_or_create_thread(user_id)
            
            # Send message
            self._send_message(thread_id, user_input)
            
            # Start run
            run_id = self._start_run(thread_id)
            
            # Wait for completion
            if not self._wait_for_completion(thread_id, run_id):
                return AIResponse(
                    text="抱歉，AI 回應逾時，請稍後再試。",
                    confidence=0.0,
                    user_id=user_id
                )
            
            # Get response
            response_text = self._get_latest_response(thread_id)
            
            if not response_text:
                return AIResponse(
                    text="抱歉，AI 無法取得回應內容，請稍後再試。",
                    confidence=0.0,
                    user_id=user_id
                )
            
            # Parse response and extract confidence
            parsed_response = self._parse_response(response_text)
            
            # Log interaction
            self.db.log_message(
                user_id=user_id,
                content=user_input,
                ai_response=parsed_response.text,
                confidence=parsed_response.confidence
            )
            
            return parsed_response
            
        except OpenAIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_response: {e}")
            raise OpenAIError(f"Unexpected error: {e}")
    
    def _parse_response(self, response_text: str) -> AIResponse:
        """Parse AI response and extract confidence score."""
        # This is a simplified version - implement actual parsing logic
        # based on your assistant's response format
        try:
            import json
            parsed = json.loads(response_text)
            return AIResponse(
                text=parsed.get("text", response_text),
                confidence=parsed.get("confidence", 1.0),
                user_id=""  # Will be set by caller
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback to plain text response
            return AIResponse(
                text=response_text,
                confidence=1.0,
                user_id=""
            )
    
    def _get_user_context(self, user_id: str) -> str:
        """
        Get user's organization context for ChatGPT.
        
        Args:
            user_id: User's LINE ID
            
        Returns:
            Formatted user context string
        """
        try:
            # Get user's organization data
            org_record = self.db.get_organization_record(user_id)
            
            if not org_record or org_record.get('completion_status') != 'complete':
                return ""
            
            # Format user context
            context_parts = []
            
            if org_record.get('organization_name'):
                context_parts.append(f"單位名稱：{org_record['organization_name']}")
            
            if org_record.get('service_city'):
                context_parts.append(f"服務縣市：{org_record['service_city']}")
            
            if org_record.get('contact_info'):
                context_parts.append(f"聯絡人資訊：{org_record['contact_info']}")
            
            if org_record.get('service_target'):
                context_parts.append(f"服務對象：{org_record['service_target']}")
            
            if context_parts:
                return "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to get user context for {user_id}: {e}")
            return ""
    
    def _refresh_user_context(self, user_id: str, thread_id: str) -> None:
        """
        Refresh user context in existing thread.
        
        Args:
            user_id: User's LINE ID
            thread_id: Thread ID to update
        """
        try:
            user_context = self._get_user_context(user_id)
            
            if user_context:
                # Add updated context message
                openai.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"我的最新基本資料：\n{user_context}"
                )
                logger.info(f"Updated user context for {user_id} in thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Failed to refresh user context for {user_id}: {e}")
    
    def reset_user_context(self, user_id: str) -> bool:
        """Reset user's conversation context."""
        try:
            self.db.reset_user_thread(user_id)
            logger.info(f"Reset context for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset context for user {user_id}: {e}")
            return False