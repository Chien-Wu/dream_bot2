"""
OpenAI service for handling AI assistant interactions.
"""
import time
import json
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass

from openai import OpenAI

from config import config
from src.utils import setup_logger, OpenAIError, TimeoutError
from src.models import AIResponse
from src.services.database_service import DatabaseService
from src.services.function_handler import FunctionHandler


logger = setup_logger(__name__)




class OpenAIService:
    """Service for OpenAI Assistant API interactions."""
    
    def __init__(self, database_service: DatabaseService, function_handler: FunctionHandler = None):
        self.config = config.openai
        self.db = database_service
        self.function_handler = function_handler
        
        # Initialize OpenAI client with v2 beta header
        self.client = OpenAI(
            api_key=self.config.api_key,
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        
        # Simple thread tracking for basic concurrency control
        self._active_threads: Dict[str, threading.Lock] = {}  # thread_id -> lock
        self._locks_lock = threading.Lock()  # For managing locks dictionary
        
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
            thread = self.client.beta.threads.create()
            
            # Add user context as first message if available
            if user_context:
                self.client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"我的基本資料：\n{user_context}\n\n我的用戶ID是：{user_id}"
                )
            
            self.db.set_user_thread_id(user_id, thread.id)
            return thread.id
        except Exception as e:
            logger.error(f"Failed to create thread for user {user_id}: {e}")
            raise OpenAIError(f"Thread creation failed: {e}")
    
    def _get_thread_lock(self, thread_id: str) -> threading.Lock:
        """Get or create a lock for the given thread."""
        with self._locks_lock:
            if thread_id not in self._active_threads:
                self._active_threads[thread_id] = threading.Lock()
            return self._active_threads[thread_id]
    
    
    
    
    
    def _send_message(self, thread_id: str, content: str) -> None:
        """Send user message to thread."""
        try:
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )
        except Exception as e:
            logger.error(f"Failed to send message to thread {thread_id}: {e}")
            if "while a run" in str(e) and "is active" in str(e):
                raise OpenAIError(f"Thread busy with active run: {e}")
            raise OpenAIError(f"Message sending failed: {e}")
    
    def _start_run(self, thread_id: str) -> str:
        """Start assistant run on thread."""
        try:
            run_params = {
                "thread_id": thread_id,
                "assistant_id": self.config.assistant_id
            }
            
            # Add function definitions if function handler is available
            # if self.function_handler:
            #     run_params["tools"] = self.function_handler.get_function_definitions()
            
            run = self.client.beta.threads.runs.create(**run_params)
            return run.id
        except Exception as e:
            logger.error(f"Failed to start run on thread {thread_id}: {e}")
            raise OpenAIError(f"Run start failed: {e}")
    
    def _wait_for_completion(self, thread_id: str, run_id: str, user_id: str) -> bool:
        """Wait for run completion with timeout and handle function calls."""
        try:
            for attempt in range(self.config.max_poll_retries):
                try:
                    run_status = self.client.beta.threads.runs.retrieve(
                        thread_id=thread_id, 
                        run_id=run_id
                    )
                    
                    if run_status.status == "completed":
                        return True
                        
                    elif run_status.status == "requires_action":
                        # Handle function calls
                        if self._handle_function_calls(thread_id, run_id, run_status, user_id):
                            continue  # Continue polling after handling function calls
                        else:
                            return False
                            
                    elif run_status.status in ["failed", "cancelled", "expired"]:
                        logger.error(f"Run {run_id} failed with status: {run_status.status}")
                        return False
                        
                    time.sleep(self.config.poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error checking run status: {e}")
                    time.sleep(self.config.poll_interval)
            
            logger.warning(f"Run {run_id} timed out after {self.config.max_poll_retries} attempts")
            return False
            
        except Exception as e:
            logger.error(f"Error in wait_for_completion: {e}")
            return False
    
    def _handle_function_calls(self, thread_id: str, run_id: str, run_status, user_id: str) -> bool:
        """Handle function calls from the assistant."""
        try:
            if not self.function_handler:
                logger.error("Function handler not available for function calls")
                return False
            
            if not run_status.required_action:
                return False
            
            tool_outputs = []
            
            # Process each tool call
            for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                if tool_call.type == "function":
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Inject the actual user_id into function arguments if needed
                    if 'user_id' in function_args and function_args['user_id'] in ['user', 'current_user', '']:
                        function_args['user_id'] = user_id
                    
                    logger.info(f"Executing function: {function_name}")
                    
                    # Execute the function
                    result = self.function_handler.execute_function(function_name, function_args)
                    
                    # Format the result for the assistant
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(result, ensure_ascii=False)
                    })
            
            # Submit tool outputs back to the run
            if tool_outputs:
                self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )
                logger.info(f"Submitted {len(tool_outputs)} tool outputs")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling function calls: {e}")
            return False
    
    def _get_latest_response(self, thread_id: str) -> Optional[str]:
        """Get the latest assistant response from thread."""
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id).data
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
        Get AI response for user input with simplified concurrency handling.
        
        Args:
            user_id: User identifier
            user_input: User's message content
            
        Returns:
            AIResponse object with text and confidence
        """
        try:
            # Get or create thread
            thread_id = self._get_or_create_thread(user_id)
            
            # Get thread-specific lock for simple concurrency control
            thread_lock = self._get_thread_lock(thread_id)
            
            with thread_lock:
                return self._process_message_immediate(user_id, user_input, thread_id)
                
        except OpenAIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_response: {e}")
            raise OpenAIError(f"Unexpected error: {e}")
    
    def _process_message_immediate(self, user_id: str, user_input: str, thread_id: str) -> AIResponse:
        """
        Process message immediately (assumes no active run).
        
        Args:
            user_id: User identifier
            user_input: User's message content
            thread_id: Thread ID to use
            
        Returns:
            AIResponse object
        """
        # Send message
        self._send_message(thread_id, user_input)
        
        # Start run
        run_id = self._start_run(thread_id)
        
        # Wait for completion
        if not self._wait_for_completion(thread_id, run_id, user_id):
            return AIResponse(
                text="抱歉，AI 回應逾時，請稍後再試。",
                confidence=0.0,
                explanation=None,
                user_id=user_id
            )
        
        # Get response
        response_text = self._get_latest_response(thread_id)
        
        if not response_text:
            return AIResponse(
                text="抱歉，AI 無法取得回應內容，請稍後再試。",
                confidence=0.0,
                explanation=None,
                user_id=user_id
            )
        
        # Parse response and extract confidence
        parsed_response = self._parse_response(response_text)
        parsed_response.user_id = user_id
        
        # Log interaction
        self.db.log_message(
            user_id=user_id,
            content=user_input,
            ai_response=parsed_response.text,
            ai_explanation=parsed_response.explanation,
            confidence=parsed_response.confidence
        )
        
        return parsed_response
    
    def _parse_response(self, response_text: str) -> AIResponse:
        """Parse AI response and extract confidence score and explanation."""
        # Parse JSON response format: {"text": "...", "explanation": "...", "confidence": 0.00}
        try:
            import json
            parsed = json.loads(response_text)
            return AIResponse(
                text=parsed.get("text", response_text),
                confidence=parsed.get("confidence", 1.0),
                explanation=parsed.get("explanation"),
                user_id=""  # Will be set by caller
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Log fallback for debugging
            logger.warning(f"Failed to parse JSON response, using fallback. Error: {e}")
            logger.warning(f"Raw response (first 200 chars): {response_text[:200]}")
            
            # Fallback to plain text response
            return AIResponse(
                text=response_text,
                confidence=1.0,
                explanation=None,
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
                context_parts.append(f"單位全名：{org_record['organization_name']}")
            
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
            # Get thread lock to prevent race conditions
            thread_lock = self._get_thread_lock(thread_id)
            
            with thread_lock:
                # Simple concurrency control - just acquire the lock
                
                user_context = self._get_user_context(user_id)
                
                if user_context:
                    # Add updated context message
                    self.client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=f"我的最新基本資料：\n{user_context}\n\n我的用戶ID是：{user_id}"
                    )
                    logger.info(f"Updated user context for {user_id} in thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Failed to refresh user context for {user_id}: {e}")
    
    def reset_user_context(self, user_id: str) -> bool:
        """Reset user's conversation context."""
        try:
            # Get the thread ID before resetting
            thread_id = self.db.get_user_thread_id(user_id)
            
            if thread_id:
                # Clean up tracking for this thread
                with self._locks_lock:
                    self._active_threads.pop(thread_id, None)
            
            self.db.reset_user_thread(user_id)
            logger.info(f"Reset context for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset context for user {user_id}: {e}")
            return False