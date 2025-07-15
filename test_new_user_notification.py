#!/usr/bin/env python3
"""
Test script to verify new user notification functionality.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from src.services.line_service import LineService
from src.utils import setup_logger

logger = setup_logger(__name__)

def test_new_user_notification():
    """Test the new user notification system."""
    
    print("🧪 Testing New User Notification System")
    print("=" * 50)
    
    # Check configuration
    admin_id = config.line.admin_user_id
    if not admin_id:
        print("❌ LINE_ADMIN_USER_ID not configured!")
        print("   Please set LINE_ADMIN_USER_ID in your .env file")
        return False
    
    print(f"✅ Admin User ID configured: {admin_id}")
    
    # Test notification
    try:
        line_service = LineService()
        
        # Simulate new user follow event
        new_user_id = "U_test_new_user_123456789"
        
        print(f"\n🔔 Simulating new user follow event...")
        print(f"   New User ID: {new_user_id}")
        
        # Send admin notification (same as in webhook controller)
        line_service.notify_admin(
            user_id=new_user_id,
            user_msg="新用戶加入 LINE Bot"
        )
        
        # Send welcome message to new user (simulation)
        welcome_message = "歡迎使用 Dream Bot！有什麼可以幫助您的嗎？"
        print(f"   Welcome message would be sent: '{welcome_message}'")
        
        print(f"\n✅ New user notification sent successfully!")
        print(f"   📱 Check your LINE account (admin) for the notification")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing notification: {e}")
        return False

def show_notification_details():
    """Show details about the notification system."""
    
    print(f"\n📋 New User Notification Details")
    print("=" * 50)
    
    print(f"🎯 When Triggered:")
    print(f"   • User adds/follows the LINE Bot")
    print(f"   • LINE sends FollowEvent webhook")
    print(f"   • Bot automatically processes the event")
    
    print(f"\n📤 What Gets Sent:")
    print(f"   • Admin notification with new user's ID")
    print(f"   • Welcome message to the new user")
    print(f"   • System log entry for monitoring")
    
    print(f"\n⚙️ Configuration:")
    print(f"   • Admin User ID: {config.line.admin_user_id or 'NOT SET'}")
    print(f"   • Notification enabled: {'Yes' if config.line.admin_user_id else 'No'}")
    
    print(f"\n📝 Admin Notification Format:")
    print(f"   用戶需要人工協助")
    print(f"   ")
    print(f"   用戶ID: [New User's LINE ID]")
    print(f"   用戶訊息: 新用戶加入 LINE Bot")
    
    print(f"\n👋 Welcome Message:")
    print(f"   '歡迎使用 Dream Bot！有什麼可以幫助您的嗎？'")

if __name__ == "__main__":
    print("🔔 New User Notification Test")
    
    success = test_new_user_notification()
    show_notification_details()
    
    if success:
        print(f"\n✅ Test completed successfully!")
        print(f"💡 The system is ready to notify admins about new users")
    else:
        print(f"\n❌ Test failed!")
        print(f"🔧 Please check your configuration and try again")