#!/usr/bin/env python3
"""
Test script to demonstrate rapid message handling.
"""
import os
import sys
import time
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import Message
from src.core.message_queue import MessageQueue
from src.utils import setup_logger

logger = setup_logger(__name__)

def test_rapid_message_scenarios():
    """Test various rapid message scenarios."""
    
    print("🧪 Testing Rapid Message Handling Scenarios")
    print("=" * 60)
    
    # Create test queue with strict limits for demonstration
    test_queue = MessageQueue(
        max_queue_size=5,
        rate_limit_window=10,  # 10 seconds
        max_messages_per_window=8,
        duplicate_threshold=2.0,
        processing_delay=0.5
    )
    
    user_id = "test_user_rapid"
    
    # Scenario 1: Normal message flow
    print("\n📝 Scenario 1: Normal Message Flow")
    messages = [
        "Hello",
        "How are you?", 
        "What's the weather?"
    ]
    
    for i, content in enumerate(messages):
        message = Message(content=content, user_id=user_id, reply_token=f"token_{i}")
        added = test_queue.add_message(message)
        print(f"  Message '{content}': {'✅ Added' if added else '❌ Rejected'}")
        time.sleep(1)  # Normal timing
    
    # Scenario 2: Rapid consecutive messages
    print("\n📝 Scenario 2: Rapid Consecutive Messages (0.1s intervals)")
    rapid_messages = [
        "Quick message 1",
        "Quick message 2", 
        "Quick message 3",
        "Quick message 4",
        "Quick message 5"
    ]
    
    for i, content in enumerate(rapid_messages):
        message = Message(content=content, user_id=user_id, reply_token=f"rapid_{i}")
        added = test_queue.add_message(message)
        print(f"  Message '{content}': {'✅ Added' if added else '❌ Rejected'}")
        time.sleep(0.1)  # Very rapid
    
    # Scenario 3: Duplicate messages
    print("\n📝 Scenario 3: Duplicate Messages")
    duplicate_content = "This is a duplicate message"
    
    for i in range(3):
        message = Message(content=duplicate_content, user_id=user_id, reply_token=f"dup_{i}")
        added = test_queue.add_message(message)
        print(f"  Duplicate #{i+1}: {'✅ Added' if added else '❌ Rejected'}")
        time.sleep(0.5)
    
    # Scenario 4: Queue overflow
    print("\n📝 Scenario 4: Queue Overflow (exceeding max queue size)")
    
    for i in range(8):  # More than max_queue_size (5)
        message = Message(content=f"Overflow message {i+1}", user_id=user_id, reply_token=f"overflow_{i}")
        added = test_queue.add_message(message)
        queue_size = test_queue.get_queue_size(user_id)
        print(f"  Message {i+1}: {'✅ Added' if added else '❌ Rejected'} (Queue: {queue_size})")
    
    # Scenario 5: Rate limiting
    print("\n📝 Scenario 5: Rate Limiting (exceeding max messages per window)")
    
    # Send many messages quickly
    for i in range(12):  # More than max_messages_per_window (8)
        message = Message(content=f"Rate limit test {i+1}", user_id=user_id, reply_token=f"rate_{i}")
        added = test_queue.add_message(message)
        print(f"  Message {i+1}: {'✅ Added' if added else '❌ Rejected (Rate Limited)'}")
    
    # Show final statistics
    stats = test_queue.get_stats()
    print(f"\n📊 Final Statistics:")
    print(f"  Total messages: {stats.total_messages}")
    print(f"  Dropped messages: {stats.dropped_messages}")
    print(f"  Current queue length: {stats.queue_length}")

def simulate_real_user_behavior():
    """Simulate realistic user behavior patterns."""
    
    print("\n" + "=" * 60)
    print("👤 Simulating Real User Behavior Patterns")
    print("=" * 60)
    
    queue = MessageQueue()
    user_id = "real_user_sim"
    
    scenarios = [
        {
            "name": "Impatient User (rapid follow-ups)",
            "messages": ["Hello", "Are you there?", "Please respond", "Is this working?"],
            "delays": [0.2, 0.3, 0.5, 0.8]
        },
        {
            "name": "Typo Correction Pattern", 
            "messages": ["How do I setup this?", "How do I set up this?", "Actually, how do I configure this?"],
            "delays": [1.0, 2.0, 3.0]
        },
        {
            "name": "Question Burst",
            "messages": ["What's your name?", "What can you do?", "How does this work?", "Are you AI?"],
            "delays": [0.5, 0.4, 0.6, 0.3]
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🎭 {scenario['name']}")
        
        for message_content, delay in zip(scenario['messages'], scenario['delays']):
            message = Message(content=message_content, user_id=user_id, reply_token="sim_token")
            added = queue.add_message(message)
            
            queue_size = queue.get_queue_size(user_id)
            status = "✅ Queued" if added else "❌ Rejected"
            
            print(f"  '{message_content}' → {status} (Queue: {queue_size})")
            time.sleep(delay)
        
        # Clear queue between scenarios
        while queue.get_next_message(user_id):
            pass

def demonstrate_queue_benefits():
    """Demonstrate the benefits of queue management."""
    
    print("\n" + "=" * 60)
    print("🎯 Benefits of Queue Management")
    print("=" * 60)
    
    benefits = [
        {
            "issue": "Duplicate Messages",
            "solution": "Automatic deduplication within 2-second window",
            "example": "User accidentally double-clicks send button"
        },
        {
            "issue": "Rate Limiting", 
            "solution": "Max 20 messages per 60-second window per user",
            "example": "Prevents spam and abuse scenarios"
        },
        {
            "issue": "Queue Overflow",
            "solution": "Max 10 messages queued, oldest dropped if exceeded", 
            "example": "User sends many messages while offline"
        },
        {
            "issue": "Processing Order",
            "solution": "FIFO processing with 0.5s delay between messages",
            "example": "Ensures responses come in correct order"
        },
        {
            "issue": "Concurrent Processing",
            "solution": "One processing thread per user, prevents race conditions",
            "example": "Multiple users can be processed simultaneously"
        }
    ]
    
    for benefit in benefits:
        print(f"\n❌ Issue: {benefit['issue']}")
        print(f"✅ Solution: {benefit['solution']}")
        print(f"💡 Example: {benefit['example']}")

if __name__ == "__main__":
    print("🧪 Rapid Message Handling Test Suite")
    
    test_rapid_message_scenarios()
    simulate_real_user_behavior()
    demonstrate_queue_benefits()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("\n🔧 Key Features Implemented:")
    print("  • Rate limiting (20 messages/60 seconds)")
    print("  • Duplicate detection (2-second window)")
    print("  • Queue management (max 10 messages)")
    print("  • Sequential processing (0.5s delays)")
    print("  • Thread-safe operations")
    print("  • User acknowledgments for queued messages")