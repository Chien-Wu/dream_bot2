#!/usr/bin/env python3
"""
Test script to verify admin notification system.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from src.services.line_service import LineService
from src.utils import setup_logger

logger = setup_logger(__name__)

def test_admin_notification():
    """Test admin notification functionality."""
    try:
        line_service = LineService()
        
        # Check if admin user ID is configured
        print(f"Admin User ID: {config.line.admin_user_id}")
        
        if not config.line.admin_user_id:
            print("❌ Admin user ID not configured!")
            return False
            
        # Test notification
        print("🔔 Sending test notification to admin...")
        line_service.notify_admin(
            user_id="test_user_123",
            user_msg="測試人工協助請求",
            ai_reply="這是測試回覆",
            confidence=0.75
        )
        
        print("✅ Test notification sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Admin Notification System...")
    success = test_admin_notification()
    
    if success:
        print("\n✅ Admin notification system is working!")
        print("Check your LINE account for the test message.")
    else:
        print("\n❌ Admin notification system failed!")
        print("Check your configuration and credentials.")