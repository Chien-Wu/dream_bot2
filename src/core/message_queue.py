"""
Message queue manager for handling rapid consecutive messages.
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Deque, Optional

from src.utils import setup_logger
from src.models import Message


logger = setup_logger(__name__)


@dataclass
class QueueStats:
    """Statistics for message queue."""
    total_messages: int = 0
    processed_messages: int = 0
    dropped_messages: int = 0
    avg_processing_time: float = 0.0
    queue_length: int = 0


class MessageQueue:
    """
    Message queue manager to handle rapid consecutive messages.
    
    Features:
    - Rate limiting per user
    - Message buffering for rapid inputs
    - Duplicate message detection
    - Queue management with limits
    """
    
    def __init__(self, 
                 max_queue_size: int = 10,
                 rate_limit_window: int = 60,  # seconds
                 max_messages_per_window: int = 20,
                 duplicate_threshold: float = 2.0,  # seconds
                 processing_delay: float = 1.0):  # seconds
        
        self.max_queue_size = max_queue_size
        self.rate_limit_window = rate_limit_window
        self.max_messages_per_window = max_messages_per_window
        self.duplicate_threshold = duplicate_threshold
        self.processing_delay = processing_delay
        
        # User-specific queues and tracking
        self.user_queues: Dict[str, Deque[Message]] = defaultdict(deque)
        self.user_timestamps: Dict[str, Deque[float]] = defaultdict(deque)
        self.user_last_message: Dict[str, tuple] = {}  # (content, timestamp)
        self.user_processing: Dict[str, bool] = defaultdict(bool)
        
        # Statistics
        self.stats = QueueStats()
        
        # Thread locks
        self.locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
    
    def should_process_message(self, message: Message) -> tuple[bool, str]:
        """
        Check if message should be processed based on rate limiting and duplicates.
        
        Args:
            message: Incoming message
            
        Returns:
            Tuple of (should_process, reason)
        """
        user_id = message.user_id
        current_time = time.time()
        
        with self.locks[user_id]:
            # Clean old timestamps
            self._clean_old_timestamps(user_id, current_time)
            
            # Check rate limiting
            if len(self.user_timestamps[user_id]) >= self.max_messages_per_window:
                return False, "rate_limit_exceeded"
            
            # Check for duplicate messages
            if self._is_duplicate_message(user_id, message, current_time):
                return False, "duplicate_message"
            
            # Check queue size
            if len(self.user_queues[user_id]) >= self.max_queue_size:
                return False, "queue_full"
            
            return True, "ok"
    
    def add_message(self, message: Message) -> bool:
        """
        Add message to user's queue.
        
        Args:
            message: Message to add
            
        Returns:
            True if message was added, False if rejected
        """
        user_id = message.user_id
        current_time = time.time()
        
        should_process, reason = self.should_process_message(message)
        
        if not should_process:
            logger.warning(f"Message rejected for user {user_id}: {reason}")
            self.stats.dropped_messages += 1
            
            if reason == "rate_limit_exceeded":
                return self._handle_rate_limit_exceeded(message)
            elif reason == "duplicate_message":
                return self._handle_duplicate_message(message)
            elif reason == "queue_full":
                return self._handle_queue_full(message)
            
            return False
        
        with self.locks[user_id]:
            # Add to queue and tracking
            self.user_queues[user_id].append(message)
            self.user_timestamps[user_id].append(current_time)
            self.user_last_message[user_id] = (message.content, current_time)
            
            self.stats.total_messages += 1
            self.stats.queue_length = sum(len(q) for q in self.user_queues.values())
            
            logger.debug(f"Added message to queue for user {user_id}, queue size: {len(self.user_queues[user_id])}")
            
            return True
    
    def get_next_message(self, user_id: str) -> Optional[Message]:
        """
        Get next message from user's queue.
        
        Args:
            user_id: User ID
            
        Returns:
            Next message or None if queue is empty
        """
        with self.locks[user_id]:
            if self.user_queues[user_id]:
                message = self.user_queues[user_id].popleft()
                self.stats.queue_length = sum(len(q) for q in self.user_queues.values())
                return message
            return None
    
    def is_user_processing(self, user_id: str) -> bool:
        """Check if user has messages being processed."""
        return self.user_processing.get(user_id, False)
    
    def set_user_processing(self, user_id: str, processing: bool):
        """Set user processing status."""
        self.user_processing[user_id] = processing
        if processing:
            logger.debug(f"Started processing for user {user_id}")
        else:
            logger.debug(f"Finished processing for user {user_id}")
    
    def get_queue_size(self, user_id: str) -> int:
        """Get current queue size for user."""
        return len(self.user_queues[user_id])
    
    def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        self.stats.queue_length = sum(len(q) for q in self.user_queues.values())
        return self.stats
    
    def _clean_old_timestamps(self, user_id: str, current_time: float):
        """Remove timestamps older than rate limit window."""
        cutoff_time = current_time - self.rate_limit_window
        while (self.user_timestamps[user_id] and 
               self.user_timestamps[user_id][0] < cutoff_time):
            self.user_timestamps[user_id].popleft()
    
    def _is_duplicate_message(self, user_id: str, message: Message, current_time: float) -> bool:
        """Check if message is a duplicate of recent message."""
        if user_id not in self.user_last_message:
            return False
        
        last_content, last_time = self.user_last_message[user_id]
        
        # Check if same content within threshold time
        if (message.content == last_content and 
            current_time - last_time < self.duplicate_threshold):
            return True
        
        return False
    
    def _handle_rate_limit_exceeded(self, message: Message) -> bool:
        """Handle rate limit exceeded scenario."""
        # Could implement queuing or user notification here
        logger.warning(f"Rate limit exceeded for user {message.user_id}")
        return False
    
    def _handle_duplicate_message(self, message: Message) -> bool:
        """Handle duplicate message scenario."""
        logger.debug(f"Duplicate message ignored for user {message.user_id}")
        return False
    
    def _handle_queue_full(self, message: Message) -> bool:
        """Handle queue full scenario."""
        user_id = message.user_id
        
        # Drop oldest message and add new one
        with self.locks[user_id]:
            if self.user_queues[user_id]:
                dropped = self.user_queues[user_id].popleft()
                logger.warning(f"Dropped oldest message for user {user_id}: {dropped.content[:50]}...")
                
            self.user_queues[user_id].append(message)
            
        return True


# Global message queue instance
message_queue = MessageQueue()