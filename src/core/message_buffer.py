"""
Message buffer manager for collecting and batching user messages.
Handles short, incomplete sentences by buffering them and sending to AI after idle period.
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Deque
from datetime import datetime

from config import config
from src.utils import setup_logger
from src.models import Message


logger = setup_logger(__name__)


@dataclass
class BufferedMessage:
    """A message in the buffer with metadata."""
    message: Message
    timestamp: float
    sequence: int


@dataclass
class UserBuffer:
    """Buffer for a specific user's messages."""
    user_id: str
    messages: Deque[BufferedMessage]
    last_activity: float
    timer: Optional[threading.Timer]
    sequence_counter: int
    is_processing: bool
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages = deque()
        self.last_activity = time.time()
        self.timer = None
        self.sequence_counter = 0
        self.is_processing = False


class MessageBufferManager:
    """
    Manages message buffering for users who send short, incomplete messages.
    
    Features:
    - Collects messages from users over a configurable timeout period
    - Combines short messages into coherent context for AI
    - Handles different user patterns (some need buffering, others don't)
    - Configurable through environment variables
    """
    
    def __init__(self):
        self.config = config.message_buffer
        self.user_buffers: Dict[str, UserBuffer] = {}
        self.locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.process_callback: Optional[Callable] = None
        
        logger.info(f"Message buffer initialized - timeout: {self.config.timeout}s, "
                   f"max_size: {self.config.max_size}, min_length: {self.config.min_length}")
    
    def set_process_callback(self, callback: Callable[[str, str, str], None]):
        """
        Set the callback function to process buffered messages.
        
        Args:
            callback: Function(user_id, combined_message, reply_token) -> None
        """
        self.process_callback = callback
    
    def should_buffer_message(self, message: Message) -> bool:
        """
        Determine if a message should be buffered based on content and user pattern.
        
        Args:
            message: Incoming message
            
        Returns:
            True if message should be buffered
        """
        # Don't buffer handover requests
        if any(keyword in message.content.lower() for keyword in ["轉人工", "人工客服", "真人", "客服"]):
            return False
        
        # Don't buffer long messages (they're likely complete thoughts)
        if len(message.content) >= self.config.min_length:
            return False
        
        # Don't buffer if user has no recent activity (first message)
        user_id = message.user_id
        if user_id not in self.user_buffers:
            return True  # Start buffering for new users with short messages
        
        # Buffer if user has been active recently
        user_buffer = self.user_buffers[user_id]
        time_since_last = time.time() - user_buffer.last_activity
        
        # If it's been too long, don't buffer (treat as new conversation)
        if time_since_last > self.config.timeout * 2:
            return False
            
        return True
    
    def add_message(self, message: Message) -> bool:
        """
        Add a message to the buffer or process immediately.
        
        Args:
            message: Incoming message
            
        Returns:
            True if message was buffered, False if processed immediately
        """
        user_id = message.user_id
        
        with self.locks[user_id]:
            # Check if message should be buffered
            if not self.should_buffer_message(message):
                logger.debug(f"Message not buffered for user {user_id}: too long or special")
                return False
            
            # Initialize user buffer if needed
            if user_id not in self.user_buffers:
                self.user_buffers[user_id] = UserBuffer(user_id)
                logger.debug(f"Created new buffer for user {user_id}")
            
            user_buffer = self.user_buffers[user_id]
            
            # If already processing, don't buffer
            if user_buffer.is_processing:
                logger.debug(f"User {user_id} buffer is processing, message not buffered")
                return False
            
            # Add message to buffer
            buffered_msg = BufferedMessage(
                message=message,
                timestamp=time.time(),
                sequence=user_buffer.sequence_counter
            )
            user_buffer.messages.append(buffered_msg)
            user_buffer.last_activity = time.time()
            user_buffer.sequence_counter += 1
            
            # Cancel existing timer if any
            if user_buffer.timer:
                user_buffer.timer.cancel()
            
            # Check if buffer is full
            if len(user_buffer.messages) >= self.config.max_size:
                logger.info(f"Buffer full for user {user_id}, processing immediately")
                self._process_buffer(user_id)
            else:
                # Set new timer
                user_buffer.timer = threading.Timer(
                    self.config.timeout,
                    self._process_buffer,
                    args=[user_id]
                )
                user_buffer.timer.start()
                
                logger.debug(f"Message buffered for user {user_id} "
                           f"({len(user_buffer.messages)}/{self.config.max_size}), "
                           f"timeout: {self.config.timeout}s")
            
            return True
    
    def force_process_user_buffer(self, user_id: str) -> bool:
        """
        Force process a user's buffer immediately.
        
        Args:
            user_id: User ID to process
            
        Returns:
            True if buffer was processed, False if no buffer exists
        """
        with self.locks[user_id]:
            if user_id in self.user_buffers and self.user_buffers[user_id].messages:
                self._process_buffer(user_id)
                return True
            return False
    
    def _process_buffer(self, user_id: str):
        """
        Process buffered messages for a user.
        
        Args:
            user_id: User ID to process buffer for
        """
        with self.locks[user_id]:
            if user_id not in self.user_buffers:
                return
            
            user_buffer = self.user_buffers[user_id]
            
            if not user_buffer.messages or user_buffer.is_processing:
                return
            
            user_buffer.is_processing = True
            
            # Cancel timer if still running
            if user_buffer.timer:
                user_buffer.timer.cancel()
                user_buffer.timer = None
            
            # Collect all messages
            messages = list(user_buffer.messages)
            user_buffer.messages.clear()
            
            logger.info(f"Processing buffer for user {user_id} with {len(messages)} messages")
            
            try:
                # Combine messages into single context
                combined_content = self._combine_messages(messages)
                
                # Use the last message's reply token (most recent)
                reply_token = messages[-1].message.reply_token if messages else None
                
                # Send acknowledgment if multiple messages
                if len(messages) > 1 and self.process_callback:
                    self._send_buffer_acknowledgment(user_id, len(messages))
                
                # Process combined message
                if self.process_callback and combined_content:
                    self.process_callback(user_id, combined_content, reply_token)
                
                logger.info(f"Successfully processed buffer for user {user_id}")
                
            except Exception as e:
                logger.error(f"Error processing buffer for user {user_id}: {e}")
                
                # Try to process individual messages as fallback
                if self.process_callback:
                    for buffered_msg in messages:
                        try:
                            self.process_callback(
                                user_id,
                                buffered_msg.message.content,
                                buffered_msg.message.reply_token
                            )
                        except Exception as fallback_error:
                            logger.error(f"Fallback processing failed: {fallback_error}")
            
            finally:
                user_buffer.is_processing = False
    
    def _combine_messages(self, messages: List[BufferedMessage]) -> str:
        """
        Combine multiple messages into a coherent context.
        
        Args:
            messages: List of buffered messages
            
        Returns:
            Combined message content
        """
        if not messages:
            return ""
        
        if len(messages) == 1:
            return messages[0].message.content
        
        # Sort by sequence to maintain order
        sorted_messages = sorted(messages, key=lambda x: x.sequence)
        
        # Combine with context markers
        combined_parts = []
        
        # Add timestamp context for the conversation
        first_time = datetime.fromtimestamp(sorted_messages[0].timestamp)
        last_time = datetime.fromtimestamp(sorted_messages[-1].timestamp)
        duration = sorted_messages[-1].timestamp - sorted_messages[0].timestamp
        
        combined_parts.append(f"[用戶在 {duration:.1f} 秒內發送了 {len(messages)} 條相關訊息]")
        
        # Combine messages with natural flow
        for i, buffered_msg in enumerate(sorted_messages, 1):
            content = buffered_msg.message.content.strip()
            if content:
                combined_parts.append(f"{content}")
        
        combined_parts.append("[以上為完整對話內容，請整合理解並回覆]")
        
        result = "\n".join(combined_parts)
        
        logger.debug(f"Combined {len(messages)} messages into: {result[:100]}...")
        
        return result
    
    def _send_buffer_acknowledgment(self, user_id: str, message_count: int):
        """
        Send acknowledgment that messages are being processed.
        
        Args:
            user_id: User ID
            message_count: Number of messages being processed
        """
        try:
            # Import here to avoid circular imports
            from src.core import container
            from src.services import LineService
            
            line_service = container.resolve(LineService)
            ack_message = f"正在整理您的 {message_count} 條訊息並回覆..."
            
            line_service.push_message(user_id, ack_message)
            logger.debug(f"Sent buffer acknowledgment to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to send buffer acknowledgment: {e}")
    
    def get_buffer_status(self, user_id: str) -> dict:
        """
        Get status of user's buffer.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with buffer status
        """
        with self.locks[user_id]:
            if user_id not in self.user_buffers:
                return {
                    'exists': False,
                    'message_count': 0,
                    'is_processing': False,
                    'time_since_last': None
                }
            
            user_buffer = self.user_buffers[user_id]
            time_since_last = time.time() - user_buffer.last_activity
            
            return {
                'exists': True,
                'message_count': len(user_buffer.messages),
                'is_processing': user_buffer.is_processing,
                'time_since_last': time_since_last,
                'has_timer': user_buffer.timer is not None
            }
    
    def clear_user_buffer(self, user_id: str):
        """
        Clear a user's buffer.
        
        Args:
            user_id: User ID
        """
        with self.locks[user_id]:
            if user_id in self.user_buffers:
                user_buffer = self.user_buffers[user_id]
                
                if user_buffer.timer:
                    user_buffer.timer.cancel()
                
                user_buffer.messages.clear()
                user_buffer.is_processing = False
                
                logger.info(f"Cleared buffer for user {user_id}")
    
    def get_stats(self) -> dict:
        """Get overall buffer statistics."""
        total_buffers = len(self.user_buffers)
        total_messages = sum(len(buf.messages) for buf in self.user_buffers.values())
        processing_buffers = sum(1 for buf in self.user_buffers.values() if buf.is_processing)
        
        return {
            'total_buffers': total_buffers,
            'total_buffered_messages': total_messages,
            'processing_buffers': processing_buffers,
            'config': {
                'timeout': self.config.timeout,
                'max_size': self.config.max_size,
                'min_length': self.config.min_length
            }
        }


# Global message buffer instance
message_buffer = MessageBufferManager()