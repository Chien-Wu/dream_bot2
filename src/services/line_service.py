"""
LINE messaging service for handling LINE Bot interactions.
"""
from typing import List, Optional
import time
import re

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
        self._user_cache = {}  # Cache for user profiles
    
    def get_user_nickname(self, user_id: str) -> str:
        """
        Get user's display name/nickname from LINE profile.
        
        Args:
            user_id: LINE user ID
            
        Returns:
            User's display name or user_id if not available
        """
        try:
            # Check cache first
            if user_id in self._user_cache:
                return self._user_cache[user_id]
            
            # Get profile from LINE API
            profile = self.messaging_api.get_profile(user_id)
            
            display_name = profile.display_name
            
            # Cache the result
            self._user_cache[user_id] = display_name
            
            return display_name
            
        except Exception as e:
            logger.warning(f"Failed to get user profile for {user_id}: {e}")
            # Return user_id as fallback
            return user_id
    
    def _split_text_by_chinese_period(self, text: str) -> List[str]:
        """
        Split text by Chinese periods (。) and clean up empty segments.
        
        Args:
            text: Text to split
            
        Returns:
            List of text segments
        """
        # Split by Chinese period and filter out empty strings
        segments = [segment.strip() for segment in text.split('。') if segment.strip()]
        
        # If no Chinese periods found, return original text as single segment
        if len(segments) <= 1:
            return [text.strip()]
            
        # Add period back to each segment except the last one (if it doesn't end with punctuation)
        result = []
        for i, segment in enumerate(segments):
            if i < len(segments) - 1:
                # Add period back to all segments except last
                result.append(segment + '。')
            else:
                # Last segment - only add period if original text ended with one
                if text.rstrip().endswith('。'):
                    result.append(segment + '。')
                else:
                    result.append(segment)
        
        return result

    def reply_message(self, reply_token: str, text: str) -> None:
        """
        Reply to a message using reply token.
        Splits long text by Chinese periods and sends as separate messages.
        
        Args:
            reply_token: LINE reply token
            text: Message text to send
        """
        try:
            # Split text by Chinese periods
            text_segments = self._split_text_by_chinese_period(text)
            
            if len(text_segments) == 1:
                # Single message - use reply
                self.messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[LineTextMessage(text=text_segments[0])]
                    )
                )
                logger.info(f"Replied to message with token: {reply_token[:10]}...")
            else:
                # Multiple segments - reply with first, then push the rest
                # Reply with first segment
                self.messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[LineTextMessage(text=text_segments[0])]
                    )
                )
                logger.info(f"Replied with first segment: {reply_token[:10]}...")
                
                # Note: We need user_id to push additional messages
                # This will be handled in reply_message_to_user method
                
        except Exception as e:
            logger.error(f"Failed to reply message: {e}")
            raise LineAPIError(f"Reply failed: {e}")

    def reply_message_to_user(self, reply_token: str, user_id: str, text: str) -> None:
        """
        Reply to a message and send additional segments as push messages.
        
        Args:
            reply_token: LINE reply token
            user_id: LINE user ID for push messages
            text: Message text to send
        """
        try:
            # Split text by Chinese periods
            text_segments = self._split_text_by_chinese_period(text)
            
            if len(text_segments) == 1:
                # Single message - use reply
                self.messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[LineTextMessage(text=text_segments[0])]
                    )
                )
                logger.info(f"Replied to message with token: {reply_token[:10]}...")
            else:
                # Multiple segments - reply with first, then push the rest
                # Reply with first segment
                self.messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[LineTextMessage(text=text_segments[0])]
                    )
                )
                logger.info(f"Replied with first segment: {reply_token[:10]}...")
                
                # Push remaining segments with small delay
                for i, segment in enumerate(text_segments[1:], 1):
                    time.sleep(0.5)  # Small delay between messages
                    self.push_message(user_id, segment)
                    logger.info(f"Pushed segment {i+1}/{len(text_segments)} to user: {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to reply message to user: {e}")
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

    def push_message_with_split(self, user_id: str, text: str) -> None:
        """
        Push a message to a user, splitting by Chinese periods if needed.
        
        Args:
            user_id: LINE user ID
            text: Message text to send
        """
        try:
            # Split text by Chinese periods
            text_segments = self._split_text_by_chinese_period(text)
            
            # Send all segments as push messages with delay
            for i, segment in enumerate(text_segments):
                if i > 0:  # Add delay between messages
                    time.sleep(0.5)
                self.push_message(user_id, segment)
                logger.info(f"Pushed segment {i+1}/{len(text_segments)} to user: {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to push split message to {user_id}: {e}")
            raise LineAPIError(f"Push split failed: {e}")
    
    def notify_admin(self, user_id: str, user_msg: str, 
                    ai_reply: str = None, confidence: float = None,
                    notification_type: str = "handover") -> None:
        """
        Notify admin about user interaction requiring attention.
        
        Args:
            user_id: User ID who sent the message
            user_msg: User's original message
            ai_reply: AI's response (if any)
            confidence: AI confidence score (if any)
            notification_type: Type of notification (handover, new_user, org_complete, image)
        """
        if not self.config.admin_user_id:
            logger.warning("Admin user ID not configured, skipping notification")
            return
            
        try:
            # Get user nickname
            user_nickname = self.get_user_nickname(user_id)
            
            # Set notification title based on type
            titles = {
                "handover": "用戶需要人工協助",
                "new_user": "新用戶加入",
                "org_complete": "組織資料完成建檔",
                "image": "用戶傳送圖片",
                "low_confidence": "AI回覆信心度偏低"
            }
            
            title = titles.get(notification_type, "用戶需要人工協助")
            
            notification_text = f"{title}\n\n"
            notification_text += f"用戶: {user_nickname}\n"
            notification_text += f"用戶訊息: {user_msg}\n"
            
            if ai_reply:
                notification_text += f"AI回覆: {ai_reply}\n"
            if confidence is not None:
                notification_text += f"信心度: {confidence:.2f}\n"
            
            self.push_message(self.config.admin_user_id, notification_text)
            logger.info(f"Notified admin about user {user_nickname} ({notification_type})")
            
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