#!/usr/bin/env python3
"""
Test script to verify Chinese period message splitting functionality.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.line_service import LineService
from src.utils import setup_logger

logger = setup_logger(__name__)

def test_chinese_period_splitting():
    """Test Chinese period splitting functionality."""
    line_service = LineService()
    
    test_cases = [
        "這是第一句話。這是第二句話。這是第三句話。",
        "單一句話沒有句號",
        "這是第一句。這是第二句",
        "這句有句號。這句也有。最後一句沒有",
        "Hello world. This is English.",
        "混合文字。Mixed content. 最後一句。",
        "。。空句號測試。。",
        "正常句子。。。多個句號。"
    ]
    
    print("🧪 Testing Chinese Period Splitting...")
    print("=" * 60)
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}:")
        print(f"Input: '{test_text}'")
        
        segments = line_service._split_text_by_chinese_period(test_text)
        
        print(f"Segments ({len(segments)}):")
        for j, segment in enumerate(segments, 1):
            print(f"  {j}. '{segment}'")
        
        print(f"Total messages that would be sent: {len(segments)}")

def test_message_flow():
    """Test the complete message flow with splitting."""
    print("\n" + "=" * 60)
    print("🔄 Testing Complete Message Flow...")
    
    line_service = LineService()
    
    # Test long message
    long_message = "歡迎使用我們的服務。我們提供專業的AI助手功能。如果您有任何問題，請隨時聯繫我們。感謝您的使用。"
    
    print(f"\n📤 Long message to be sent:")
    print(f"'{long_message}'")
    
    segments = line_service._split_text_by_chinese_period(long_message)
    
    print(f"\n📨 Message delivery simulation:")
    print(f"Total segments: {len(segments)}")
    
    if len(segments) == 1:
        print("✉️  Single reply message would be sent")
    else:
        print("✉️  Reply message (first segment):")
        print(f"    '{segments[0]}'")
        
        print("📬 Push messages (remaining segments):")
        for i, segment in enumerate(segments[1:], 2):
            print(f"    {i}. '{segment}' (delay: 0.5s)")

if __name__ == "__main__":
    print("🧪 Testing Chinese Period Message Splitting")
    
    test_chinese_period_splitting()
    test_message_flow()
    
    print("\n" + "=" * 60)
    print("✅ Testing completed!")
    print("\n💡 How it works:")
    print("1. Long messages are split by Chinese periods (。)")
    print("2. First segment sent as reply message")
    print("3. Remaining segments sent as push messages with 0.5s delay")
    print("4. This creates a natural conversation flow")