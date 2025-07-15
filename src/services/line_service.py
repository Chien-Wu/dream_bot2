"""
LINE messaging service for handling LINE Bot interactions.
"""
from typing import List, Optional

from linebot.v3.messaging import (
    MessagingApi, Configuration, ApiClient, 
    ReplyMessageRequest, PushMessageRequest
)
from linebot.v3.messaging import TextMessage as LineTextMessage
from linebot.v3.webhook import MessageEvent

from config import config
from src.utils import setup_logger, LineAPIError
from src.models import Message


logger = setup_logger(__name__)


class LineService:
    """Service for LINE messaging operations."""
    
    def __init__(self):
        self.config = config.line
        line_config = Configuration(access_token=self.config.channel_access_token)
        self.messaging_api = MessagingApi(ApiClient(line_config))
    
    def reply_message(self, reply_token: str, text: str) -> None:
        """
        Reply to a message using reply token.
        
        Args:
            reply_token: LINE reply token
            text: Message text to send
        """
        try:
            self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[LineTextMessage(text=text)]
                )
            )
            logger.info(f"Replied to message with token: {reply_token[:10]}...")
            
        except Exception as e:
            logger.error(f"Failed to reply message: {e}")
            raise LineAPIError(f"Reply failed: {e}")
    
    def push_message(self, user_id: str, text: str) -> None:
        """
        Push a message to a user.
        
        Args:
            user_id: LINE user ID
            text: Message text to send
        """
        try:
            self.messaging_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[LineTextMessage(text=text)]
                )
            )
            logger.info(f"Pushed message to user: {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to push message to {user_id}: {e}")
            raise LineAPIError(f"Push failed: {e}")
    
    def notify_admin(self, user_id: str, user_msg: str, 
                    ai_reply: str = None, confidence: float = None) -> None:
        """
        Notify admin about user interaction requiring attention.
        
        Args:
            user_id: User ID who sent the message
            user_msg: User's original message
            ai_reply: AI's response (if any)
            confidence: AI confidence score (if any)
        """
        if not self.config.admin_user_id:
            logger.warning("Admin user ID not configured, skipping notification")
            return
            
        try:
            notification_text = f"用戶需要人工協助\n\n"
            notification_text += f"用戶ID: {user_id}\n"
            notification_text += f"用戶訊息: {user_msg}\n"
            
            if ai_reply:
                notification_text += f"AI回覆: {ai_reply}\n"
            if confidence is not None:
                notification_text += f"信心度: {confidence:.2f}\n"
            
            self.push_message(self.config.admin_user_id, notification_text)
            logger.info(f"Notified admin about user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
            # Don't raise exception to avoid disrupting main flow
    
    def extract_message(self, event: MessageEvent) -> Optional[Message]:
        """
        Extract message data from LINE event.
        
        Args:
            event: LINE message event
            
        Returns:
            Message object or None if invalid
        """
        try:
            # Skip group messages
            if (hasattr(event.source, "group_id") and event.source.group_id) or \
               (hasattr(event.source, "room_id") and event.source.room_id):
                return None
            
            message_type = type(event.message).__name__
            
            # Handle different message types
            if message_type == "StickerMessageContent":
                return None  # Ignore stickers
            
            if message_type == "ImageMessageContent":
                return Message(
                    content="[Image]",
                    user_id=event.source.user_id,
                    message_type="image",
                    reply_token=event.reply_token
                )
            
            if not hasattr(event.message, 'text'):
                return None  # Ignore non-text messages
            
            user_input = event.message.text.strip()
            if not user_input:
                return None
            
            return Message(
                content=user_input,
                user_id=event.source.user_id,
                message_type="text",
                reply_token=event.reply_token
            )
            
        except Exception as e:
            logger.error(f"Failed to extract message from event: {e}")
            return None
    
    def is_handover_request(self, message_text: str) -> bool:
        """
        Check if message is requesting human handover.
        
        Args:
            message_text: User's message text
            
        Returns:
            True if handover is requested
        """
        handover_keywords = ["轉人工", "人工客服", "真人", "客服"]
        return any(keyword in message_text.lower() for keyword in handover_keywords)