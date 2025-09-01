"""
Message buffer manager for collecting and batching user messages.
Handles short, incomplete sentences by buffering them and sending to AI after idle period.
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Deque

from config import config
from src.utils import setup_logger, count_chinese_characters
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
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages = deque()
        self.last_activity = time.time()
        self.timer = None
        self.sequence_counter = 0


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
        
        logger.info(f"Message buffer initialized - timeout: {self.config.timeout}s, max_size: {self.config.max_size}")
    
    def set_process_callback(self, callback: Callable[[str, str, str], None]):
        """
        Set the callback function to process buffered messages.
        
        Args:
            callback: Function(user_id, combined_message, reply_token) -> None
        """
        self.process_callback = callback
    
    
    def _cancel_timer(self, user_buffer: UserBuffer):
        """Cancel timer for user buffer."""
        if user_buffer.timer:
            user_buffer.timer.cancel()
            user_buffer.timer = None
    
    def _clear_user_buffer_internal(self, user_buffer: UserBuffer):
        """Clear user buffer messages and timer."""
        user_buffer.messages.clear()
        self._cancel_timer(user_buffer)
    
    def _ensure_user_buffer_exists(self, user_id: str):
        """Ensure user buffer exists."""
        if user_id not in self.user_buffers:
            self.user_buffers[user_id] = UserBuffer(user_id)
            logger.debug(f"Created new buffer for user {user_id}")
    
    def _update_last_activity(self, user_id: str):
        """Update last activity timestamp for user."""
        current_time = time.time()
        if user_id in self.user_buffers:
            self.user_buffers[user_id].last_activity = current_time
        return current_time
    
    def _would_exceed_char_limit(self, user_buffer: UserBuffer, new_content: str) -> bool:
        """Check if adding new content would exceed Chinese character limit."""
        if not user_buffer.messages:
            return False
        
        current_combined = self._combine_messages(user_buffer.messages)
        current_chars = count_chinese_characters(current_combined)
        new_chars = count_chinese_characters(new_content)
        
        return current_chars + new_chars > self.config.max_chinese_chars

    def should_buffer_message(self, message: Message) -> bool:
        """
        Determine if a message should be buffered. Buffer everything, with character limit checks.
        
        Args:
            message: Incoming message
            
        Returns:
            True if message should be buffered
        """
        user_id = message.user_id
        content = message.content
        
        # Ensure user buffer exists
        self._ensure_user_buffer_exists(user_id)
        
        # Check if adding this message would exceed Chinese character limit
        user_buffer = self.user_buffers[user_id]
        if self._would_exceed_char_limit(user_buffer, content):
            logger.info(f"Message would exceed {self.config.max_chinese_chars} Chinese character limit for user {user_id}, processing current buffer first")
            return False  # Process current buffer first, then this message will start new buffer
        
        logger.info(f"Message will be buffered for user {user_id}: '{content[:50]}...' (length: {len(content)})")
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
                logger.debug(f"Message not buffered for user {user_id}")
                return False
            
            user_buffer = self.user_buffers[user_id]  # Buffer exists from should_buffer_message
            
            # Add message to buffer and update activity
            current_time = self._update_last_activity(user_id)
            buffered_msg = BufferedMessage(
                message=message,
                timestamp=current_time,
                sequence=user_buffer.sequence_counter
            )
            user_buffer.messages.append(buffered_msg)
            user_buffer.sequence_counter += 1
            
            # Check if buffer is full by message count
            if len(user_buffer.messages) >= self.config.max_size:
                # Cancel existing timer since we're processing immediately
                self._cancel_timer(user_buffer)
                
                logger.info(f"Buffer full (message count) for user {user_id}, processing immediately")
                self._process_buffer(user_id)
            else:
                # Only set timer if one doesn't exist yet
                if user_buffer.timer is None:
                    user_buffer.timer = threading.Timer(
                        self.config.timeout,
                        self._process_buffer,
                        args=[user_id]
                    )
                    user_buffer.timer.start()
                    logger.debug(f"Started buffer timer for user {user_id}")
                
                logger.debug(f"Message buffered for user {user_id} ({len(user_buffer.messages)}/{self.config.max_size})")
            
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
        Process buffered messages for a user using atomic snapshot-and-clear.
        
        Args:
            user_id: User ID to process buffer for
        """
        # Atomic snapshot and delete - do this under lock
        messages_to_process = None
        reply_token = None
        
        with self.locks[user_id]:
            if user_id not in self.user_buffers:
                return
            
            user_buffer = self.user_buffers[user_id]
            
            if not user_buffer.messages:
                return
            
            # ATOMIC: Take snapshot of messages and delete entire user buffer
            messages_to_process = list(user_buffer.messages)
            self._cancel_timer(user_buffer)
            
            # Delete entire user buffer (not just clear) - fresh start for next messages
            del self.user_buffers[user_id]
            
            # Get reply token from last message
            reply_token = messages_to_process[-1].message.reply_token if messages_to_process else None
        
        # Process messages OUTSIDE the lock - don't block new message collection
        if messages_to_process:
            self._process_messages_in_background(user_id, messages_to_process, reply_token)
    
    def _process_messages_in_background(self, user_id: str, messages: List[BufferedMessage], reply_token: str):
        """
        Process messages in background without blocking buffer collection.
        
        Args:
            user_id: User ID
            messages: Messages to process
            reply_token: Reply token for response
        """
        logger.info(f"Processing buffer for user {user_id} with {len(messages)} messages")
        
        try:
            # Combine messages into single context
            combined_content = self._combine_messages(messages)
            
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
    
    
    def _combine_messages(self, messages: List[BufferedMessage]) -> str:
        """
        Combine multiple messages into a single string.
        
        Args:
            messages: List of buffered messages
            
        Returns:
            Combined message content as a single string
        """
        if not messages:
            return ""
        
        # Messages are added sequentially, no need to sort
        combined_parts = []
        for buffered_msg in messages:
            content = buffered_msg.message.content.strip()
            if content:
                combined_parts.append(content)
        
        # Join with spaces to create one natural sentence
        result = " ".join(combined_parts)
        
        logger.debug(f"Combined {len(combined_parts)} messages into: {result[:100]}...")
        
        return result
    
    
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
                    'time_since_last': None
                }
            
            user_buffer = self.user_buffers[user_id]
            time_since_last = time.time() - user_buffer.last_activity
            
            return {
                'exists': True,
                'message_count': len(user_buffer.messages),
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
                self._clear_user_buffer_internal(self.user_buffers[user_id])
                logger.info(f"Cleared buffer for user {user_id}")
    
    def get_stats(self) -> dict:
        """Get overall buffer statistics."""
        total_buffers = len(self.user_buffers)
        total_messages = sum(len(buf.messages) for buf in self.user_buffers.values())
        
        return {
            'total_buffers': total_buffers,
            'total_buffered_messages': total_messages,
            'config': {
                'timeout': self.config.timeout,
                'max_size': self.config.max_size,
                'min_length': self.config.min_length
            }
        }


# Global message buffer instance
message_buffer = MessageBufferManager()