#!/usr/bin/env python3
"""
Test script to verify handover detection and processing.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.line_service import LineService
from src.models import Message
from src.core.message_processor import MessageProcessor
from src.services.database_service import DatabaseService
from src.services.openai_service import OpenAIService
from src.utils import setup_logger

logger = setup_logger(__name__)

def test_handover_detection():
    """Test handover keyword detection."""
    line_service = LineService()
    
    test_messages = [
        "轉人工",
        "我要人工客服", 
        "需要真人協助",
        "客服",
        "普通問題",  # Should not trigger
        "Hello"      # Should not trigger
    ]
    
    print("🔍 Testing handover detection...")
    for msg in test_messages:
        is_handover = line_service.is_handover_request(msg)
        print(f"'{msg}' → {'✅ HANDOVER' if is_handover else '❌ Normal'}")

def test_message_processing():
    """Test complete message processing flow."""
    print("\n🔄 Testing message processing flow...")
    
    # Create services
    db_service = DatabaseService()
    openai_service = OpenAIService(db_service)
    line_service = LineService()
    processor = MessageProcessor(db_service, openai_service, line_service)
    
    # Test handover message
    handover_message = Message(
        content="轉人工",
        user_id="test_user_handover",
        message_type="text",
        reply_token="test_reply_token"
    )
    
    print("📝 Processing handover message...")
    try:
        processor.process_message(handover_message)
        print("✅ Handover message processed successfully!")
    except Exception as e:
        print(f"❌ Error processing handover: {e}")
        logger.error(f"Handover processing failed: {e}")

if __name__ == "__main__":
    print("🧪 Testing Handover Detection and Processing...")
    
    test_handover_detection()
    test_message_processing()
    
    print("\n📱 Check your LINE account for admin notifications!")