#!/usr/bin/env python3
"""
Test script to demonstrate message buffering functionality.
"""
import os
import sys
import time
import threading
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models import Message
from src.core.message_buffer import MessageBufferManager
from src.utils import setup_logger

logger = setup_logger(__name__)

def mock_process_callback(user_id: str, combined_content: str, reply_token: str):
    """Mock callback function for testing."""
    print(f"🤖 Processing combined message for {user_id}:")
    print(f"   Content: {combined_content}")
    print(f"   Reply Token: {reply_token}")
    print(f"   Length: {len(combined_content)} characters")
    print()

def test_message_buffering_scenarios():
    """Test various message buffering scenarios."""
    
    print("🧪 Testing Message Buffering Scenarios")
    print("=" * 60)
    
    # Create test buffer manager with fast timeout for testing
    buffer_manager = MessageBufferManager()
    buffer_manager.config.timeout = 3.0  # 3 seconds for testing
    buffer_manager.config.max_size = 5
    buffer_manager.config.min_length = 30
    buffer_manager.set_process_callback(mock_process_callback)
    
    user_id = "test_user_buffer"
    
    # Scenario 1: Short messages that should be buffered
    print("\n📝 Scenario 1: Short Messages (Should be buffered)")
    short_messages = [
        "你好",
        "我想問",
        "關於產品",
        "價格多少",
        "謝謝"
    ]
    
    for i, content in enumerate(short_messages):
        message = Message(content=content, user_id=user_id, reply_token=f"short_{i}")
        buffered = buffer_manager.add_message(message)
        status = buffer_manager.get_buffer_status(user_id)
        print(f"  '{content}' → {'🔄 Buffered' if buffered else '❌ Not buffered'} "
              f"(Buffer: {status['message_count']})")
        time.sleep(0.5)
    
    # Wait for timeout processing
    print(f"⏰ Waiting {buffer_manager.config.timeout} seconds for timeout processing...")
    time.sleep(buffer_manager.config.timeout + 1)
    
    # Scenario 2: Long message that should NOT be buffered
    print("\n📝 Scenario 2: Long Message (Should NOT be buffered)")
    long_message = "這是一個很長的訊息，應該不會被緩衝，而是直接處理，因為它超過了最小長度限制。"
    message = Message(content=long_message, user_id=user_id, reply_token="long_1")
    buffered = buffer_manager.add_message(message)
    print(f"  '{long_message[:30]}...' → {'🔄 Buffered' if buffered else '✅ Processed immediately'}")
    
    # Scenario 3: Buffer overflow (exceeds max size)
    print("\n📝 Scenario 3: Buffer Overflow (Exceeds max size)")
    for i in range(7):  # More than max_size (5)
        content = f"訊息 {i+1}"
        message = Message(content=content, user_id=user_id, reply_token=f"overflow_{i}")
        buffered = buffer_manager.add_message(message)
        status = buffer_manager.get_buffer_status(user_id)
        print(f"  '{content}' → {'🔄 Buffered' if buffered else '⚡ Processed'} "
              f"(Buffer: {status['message_count']})")
        time.sleep(0.2)
    
    # Scenario 4: Handover request (should not be buffered)
    print("\n📝 Scenario 4: Handover Request (Should NOT be buffered)")
    handover_message = "轉人工"
    message = Message(content=handover_message, user_id=user_id, reply_token="handover_1")
    buffered = buffer_manager.add_message(message)
    print(f"  '{handover_message}' → {'🔄 Buffered' if buffered else '✅ Processed immediately'}")

def simulate_realistic_user_patterns():
    """Simulate realistic user messaging patterns."""
    
    print("\n" + "=" * 60)
    print("👤 Simulating Realistic User Patterns")
    print("=" * 60)
    
    buffer_manager = MessageBufferManager()
    buffer_manager.config.timeout = 5.0  # 5 seconds
    buffer_manager.set_process_callback(mock_process_callback)
    
    patterns = [
        {
            "name": "User Typing Step by Step",
            "user_id": "step_user",
            "messages": ["我想買", "蘋果手機", "iPhone 15", "多少錢", "有優惠嗎"],
            "delays": [1.0, 0.8, 1.2, 0.5, 2.0]
        },
        {
            "name": "User Asking Complex Question",
            "user_id": "complex_user", 
            "messages": ["請問", "你們的", "退貨政策", "是什麼", "需要什麼條件"],
            "delays": [0.5, 0.3, 0.7, 0.4, 1.5]
        },
        {
            "name": "User Sending Complete Thought",
            "user_id": "complete_user",
            "messages": ["我想了解你們公司的產品和服務，特別是關於價格和售後服務的詳細資訊。"],
            "delays": [0]
        }
    ]
    
    for pattern in patterns:
        print(f"\n🎭 {pattern['name']}")
        user_id = pattern['user_id']
        
        for i, (content, delay) in enumerate(zip(pattern['messages'], pattern['delays'])):
            message = Message(content=content, user_id=user_id, reply_token=f"{user_id}_{i}")
            buffered = buffer_manager.add_message(message)
            
            status = buffer_manager.get_buffer_status(user_id)
            buffer_indicator = f"(Buffer: {status['message_count']})" if buffered else ""
            
            print(f"  📝 '{content}' → {'🔄 Buffered' if buffered else '✅ Immediate'} {buffer_indicator}")
            
            if delay > 0:
                time.sleep(delay)
        
        # Wait a bit to see buffer processing
        time.sleep(6)
        
        # Clear buffer for next pattern
        buffer_manager.clear_user_buffer(user_id)

def demonstrate_configuration_effects():
    """Demonstrate how different configurations affect buffering."""
    
    print("\n" + "=" * 60)
    print("⚙️ Configuration Effects Demonstration")
    print("=" * 60)
    
    configs = [
        {
            "name": "Fast Processing (2s timeout)",
            "timeout": 2.0,
            "max_size": 3,
            "min_length": 20
        },
        {
            "name": "Patient Processing (8s timeout)",
            "timeout": 8.0,
            "max_size": 8,
            "min_length": 40
        },
        {
            "name": "Strict Processing (long messages only)",
            "timeout": 5.0,
            "max_size": 5,
            "min_length": 100
        }
    ]
    
    test_messages = ["你好", "我想問", "關於價格", "多少錢"]
    
    for config_set in configs:
        print(f"\n🔧 {config_set['name']}")
        print(f"   Timeout: {config_set['timeout']}s, Max Size: {config_set['max_size']}, "
              f"Min Length: {config_set['min_length']}")
        
        buffer_manager = MessageBufferManager()
        buffer_manager.config.timeout = config_set['timeout']
        buffer_manager.config.max_size = config_set['max_size']
        buffer_manager.config.min_length = config_set['min_length']
        buffer_manager.set_process_callback(mock_process_callback)
        
        user_id = f"config_test_{config_set['name'].split()[0].lower()}"
        
        for i, content in enumerate(test_messages):
            message = Message(content=content, user_id=user_id, reply_token=f"config_{i}")
            buffered = buffer_manager.add_message(message)
            print(f"     '{content}' → {'🔄 Buffered' if buffered else '✅ Immediate'}")
            time.sleep(0.3)
        
        # Show final buffer status
        status = buffer_manager.get_buffer_status(user_id)
        if status['message_count'] > 0:
            print(f"     📊 Final buffer: {status['message_count']} messages waiting")
            time.sleep(config_set['timeout'] + 1)  # Wait for processing

def show_buffer_benefits():
    """Show the benefits of message buffering."""
    
    print("\n" + "=" * 60)
    print("💡 Benefits of Message Buffering")
    print("=" * 60)
    
    benefits = [
        {
            "problem": "用戶發送多條短訊息",
            "example": "['我想', '買手機', 'iPhone', '多少錢']",
            "without_buffer": "4 separate AI calls, fragmented context",
            "with_buffer": "1 AI call with complete context: '用戶想買iPhone手機，詢問價格'"
        },
        {
            "problem": "打字思考過程",
            "example": "['請問', '你們的', '退貨政策', '是什麼']",
            "without_buffer": "AI responds to incomplete thoughts",
            "with_buffer": "AI gets full question: '請問你們的退貨政策是什麼'"
        },
        {
            "problem": "網路延遲造成分段發送",
            "example": "['產品介紹', '在哪裡', '可以看到']",
            "without_buffer": "Confusing fragmented responses",
            "with_buffer": "Coherent response to: '產品介紹在哪裡可以看到'"
        }
    ]
    
    for benefit in benefits:
        print(f"\n❌ Problem: {benefit['problem']}")
        print(f"📝 Example: {benefit['example']}")
        print(f"🚫 Without Buffer: {benefit['without_buffer']}")
        print(f"✅ With Buffer: {benefit['with_buffer']}")

if __name__ == "__main__":
    print("🧪 Message Buffering Test Suite")
    
    test_message_buffering_scenarios()
    simulate_realistic_user_patterns()
    demonstrate_configuration_effects()
    show_buffer_benefits()
    
    print("\n" + "=" * 60)
    print("✅ All message buffering tests completed!")
    
    print("\n🎯 Key Features:")
    print("  • Configurable timeout (MESSAGE_BUFFER_TIMEOUT)")
    print("  • Maximum buffer size (MESSAGE_BUFFER_MAX_SIZE)")
    print("  • Minimum message length for immediate processing (MESSAGE_BUFFER_MIN_LENGTH)")
    print("  • Automatic context combination")
    print("  • Smart handover detection")
    print("  • Buffer overflow protection")
    print("  • User acknowledgments")
    
    print("\n⚙️ Current Configuration:")
    from config import config
    print(f"  • Timeout: {config.message_buffer.timeout}s")
    print(f"  • Max Size: {config.message_buffer.max_size}")
    print(f"  • Min Length: {config.message_buffer.min_length}")