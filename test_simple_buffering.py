#!/usr/bin/env python3
"""
Simple test for message buffering functionality.
"""
import os
import sys
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import Message
from src.core.message_buffer import MessageBufferManager

def simple_callback(user_id: str, combined_content: str, reply_token: str):
    """Simple callback for testing."""
    print(f"✅ PROCESSED: User {user_id}")
    print(f"   Combined: {combined_content}")
    print()

def test_basic_buffering():
    """Test basic buffering functionality."""
    print("🧪 Testing Basic Message Buffering")
    print("=" * 50)
    
    # Create buffer with fast settings
    buffer = MessageBufferManager()
    buffer.config.timeout = 2.0  # 2 seconds
    buffer.config.max_size = 3   # 3 messages max
    buffer.config.min_length = 20  # 20 chars min
    buffer.set_process_callback(simple_callback)
    
    user_id = "test_user"
    
    # Test 1: Short messages (should buffer)
    print("\n📝 Test 1: Short Messages")
    short_messages = ["你好", "我想問", "價格"]
    
    for i, msg in enumerate(short_messages):
        message = Message(content=msg, user_id=user_id, reply_token=f"token_{i}")
        buffered = buffer.add_message(message)
        print(f"'{msg}' → {'Buffered' if buffered else 'Immediate'}")
        time.sleep(0.3)
    
    print("⏰ Waiting 3 seconds for timeout...")
    time.sleep(3)
    
    # Test 2: Long message (should not buffer)
    print("\n📝 Test 2: Long Message")
    long_msg = "這是一個很長的訊息，應該不會被緩衝處理"
    message = Message(content=long_msg, user_id=user_id, reply_token="long_token")
    buffered = buffer.add_message(message)
    print(f"'{long_msg}' → {'Buffered' if buffered else 'Immediate'}")
    
    print("\n✅ Basic test completed!")

if __name__ == "__main__":
    test_basic_buffering()