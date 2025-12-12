"""
LINE messaging service for handling LINE Bot interactions.
"""
from typing import List, Optional, TYPE_CHECKING
import time
import re

if TYPE_CHECKING:
    from src.services.user_handover_service import UserHandoverService

from linebot.v3.messaging import (
    MessagingApi, Configuration, ApiClient, 
    ReplyMessageRequest, PushMessageRequest
)
from linebot.v3.messaging import TextMessage as LineTextMessage
from linebot.v3.webhook import MessageEvent

from config import config
from src.utils import setup_logger, LineAPIError
from src.models import Message
from src.services.database_service import DatabaseService
from src.messages import messages


logger = setup_logger(__name__)


class LineService:
    """Service for LINE messaging operations."""
    
    def __init__(self, user_handover_service: 'UserHandoverService' = None):
        self.config = config.line
        line_config = Configuration(access_token=self.config.channel_access_token)
        self.messaging_api = MessagingApi(ApiClient(line_config))
        self._user_cache = {}  # Cache for user profiles
        self.db = DatabaseService()
        self.handover_service = user_handover_service
    
    def _is_user_in_handover(self, user_id: str) -> bool:
        """
        Check if user is currently in handover mode.
        
        Args:
            user_id: User's LINE ID
            
        Returns:
            True if user is in handover mode and messages should be blocked
        """
        if not self.handover_service:
            return False
        
        try:
            return self.handover_service.is_in_handover(user_id)
        except Exception as e:
            logger.error(f"Failed to check handover status for user {user_id}: {e}")
            # Fail-safe: don't block messages if service fails
            return False
    
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
    
    def _clean_reference_brackets(self, text: str) -> str:
        """
        Clean reference brackets in the format 【訊息編號:搜尋結果編號†來源名稱】
        
        Args:
            text: Text containing reference brackets to clean
            
        Returns:
            Cleaned text without reference brackets
        """
        # Remove brackets with pattern 【...†...】
        cleaned_text = re.sub(r'【[^】]*†[^】]*】', '', text)
        
        # Replace Chinese semicolons with newlines
        cleaned_text = cleaned_text.replace('；', '\n')
        
        # Clean up any double spaces left behind and trim, but preserve newlines
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    def _format_numbered_lists(self, text: str) -> str:
        """
        Format numbered lists by adding line breaks before each number.
        
        Args:
            text: Text containing numbered lists
            
        Returns:
            Formatted text with line breaks
        """
        # Pattern to match numbered lists: digit followed by dot and space, or Chinese numbers
        # Matches: "1. ", "2. ", "一、", "二、", etc.
        chinese_pattern = f'[{messages.messages.CHINESE_NUMBERS}]+[、．]\\s*'

        # Add newlines before numbered items, but not at the start of text
        formatted_text = re.sub(r'(?<!^)(?<![\n\r])(\d+\.\s+)', r'\n\1', text)
        formatted_text = re.sub(f'(?<!^)(?<![\n\r])({chinese_pattern})', r'\n\1', formatted_text)
        
        return formatted_text
    
    def _split_text_by_sentence_endings(self, text: str) -> List[str]:
        """
        Split text by sentence ending punctuation marks including Chinese periods, question marks, and exclamation marks.
        
        Args:
            text: Text to split
            
        Returns:
            List of text segments
        """
        # Use regex to split by sentence endings while preserving the punctuation
        # Split by: 。 ？ ！ ? !
        sentence_pattern = r'([。？！?!])'
        
        # Split text and keep delimiters
        parts = re.split(sentence_pattern, text)
        
        # Reconstruct sentences by combining text with their ending punctuation
        segments = []
        for i in range(0, len(parts) - 1, 2):
            if i + 1 < len(parts):
                # Combine text part with its punctuation
                sentence = parts[i] + parts[i + 1]
                sentence = sentence.strip()
                if sentence:
                    segments.append(sentence)
        
        # Handle case where text doesn't end with punctuation
        if len(parts) % 2 == 1 and parts[-1].strip():
            segments.append(parts[-1].strip())
        
        # If no sentences found or only one sentence, return original text
        if len(segments) <= 1:
            return [text.strip()]
        
        return segments


    def send_message(self, user_id: str, text: str, reply_token: str = None) -> None:
        """
        Send message to user with automatic fallback from reply to push.
        
        Args:
            user_id: LINE user ID
            text: Message text to send
            reply_token: Optional reply token (will fallback to push if invalid)
        """
        # Check if user is in handover mode - block outgoing messages
        if self._is_user_in_handover(user_id):
            logger.info(f"Blocked outgoing message to user {user_id} - in handover mode")
            return
        
        try:
            # Process text
            processed_text = self._process_text(text)
            text_segments = self._split_text_by_sentence_endings(processed_text)
            
            # Try reply first if token available, otherwise use push
            if reply_token:
                try:
                    self._send_with_reply(reply_token, text_segments, user_id)
                    return
                except Exception as e:
                    if self._is_token_error(e):
                        logger.warning("Reply token invalid, falling back to push")
                    else:
                        raise e
            
            # Fallback to push messages
            self._send_with_push(user_id, text_segments)
            
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            raise LineAPIError(f"Message send failed: {e}")
    
    def send_raw_message(self, user_id: str, text: str, reply_token: str = None) -> None:
        """
        Send raw message without processing - used for admin commands.
        
        Args:
            user_id: LINE user ID
            text: Raw message text to send (unprocessed)
            reply_token: Optional reply token (will fallback to push if invalid)
        """
        try:
            if reply_token:
                try:
                    self.messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[LineTextMessage(text=text)]
                        )
                    )
                    logger.info("Raw reply sent successfully")
                    return
                except Exception as e:
                    if self._is_token_error(e):
                        logger.warning("Reply token invalid, falling back to push")
                    else:
                        raise e
            
            # Fallback to push
            self.push_message(user_id, text)
            
        except Exception as e:
            logger.error(f"Failed to send raw message: {e}")
            raise LineAPIError(f"Raw message send failed: {e}")
    
    def push_message(self, user_id: str, text: str) -> None:
        """
        Push a single message to a user.
        
        Args:
            user_id: LINE user ID
            text: Message text to send
        """
        # Check if user is in handover mode - block outgoing messages
        if self._is_user_in_handover(user_id):
            logger.info(f"Blocked outgoing push message to user {user_id} - in handover mode")
            return
        
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

    def _push_to_target(self, target_id: str, text: str) -> None:
        """
        Push message to specific target (user or group) without handover checks.

        Args:
            target_id: Target user ID or group ID
            text: Message text to send
        """
        if not target_id:
            logger.warning("Target ID not provided, cannot send message")
            return

        try:
            self.messaging_api.push_message(
                PushMessageRequest(
                    to=target_id,
                    messages=[LineTextMessage(text=text)]
                )
            )
            logger.info(f"Pushed message to target {target_id[:8]}...")

        except Exception as e:
            logger.error(f"Failed to push message to target: {e}")
            raise LineAPIError(f"Push to target failed: {e}")

    def push_admin_message(self, text: str) -> None:
        """
        Push message to default admin without handover checks.
        Legacy method - uses default admin target.

        Args:
            text: Message text to send to admin
        """
        self._push_to_target(self.config.admin_user_id, text)

    def _process_text(self, text: str) -> str:
        """
        Process text by cleaning reference brackets and formatting.
        
        Args:
            text: Raw text to process
            
        Returns:
            Processed text
        """
        cleaned_text = self._clean_reference_brackets(text)
        return self._format_numbered_lists(cleaned_text)
    
    def _send_with_reply(self, reply_token: str, text_segments: List[str], user_id: str) -> None:
        """
        Send message segments using reply token.
        
        Args:
            reply_token: LINE reply token
            text_segments: List of text segments to send
            user_id: User ID for additional segments
        """
        # Send first segment as reply
        self.messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[LineTextMessage(text=text_segments[0])]
            )
        )
        logger.info(f"Replied with first segment")
        
        # Send remaining segments as push messages
        for i, segment in enumerate(text_segments[1:], 1):
            time.sleep(0.5)
            self.push_message(user_id, segment)
            logger.info(f"Pushed segment {i+1}/{len(text_segments)}")
    
    def _send_with_push(self, user_id: str, text_segments: List[str]) -> None:
        """
        Send message segments using push messages.
        
        Args:
            user_id: LINE user ID
            text_segments: List of text segments to send
        """
        for i, segment in enumerate(text_segments):
            if i > 0:
                time.sleep(0.5)
            self.push_message(user_id, segment)
            logger.info(f"Pushed segment {i+1}/{len(text_segments)}")
    
    def _is_token_error(self, error: Exception) -> bool:
        """
        Check if error is related to invalid reply token.
        
        Args:
            error: Exception to check
            
        Returns:
            True if it's a token-related error
        """
        error_msg = str(error).lower()
        return "invalid reply token" in error_msg or "reply token" in error_msg
    
    def _get_admin_target_for_intent(self, intent: Optional[str]) -> Optional[str]:
        """
        Get the appropriate admin target ID based on AI intent.

        Args:
            intent: AI-detected intent (e.g., "募款", "領頭雁", etc.)

        Returns:
            Admin target ID (user or group ID), or None if not configured

        Intent Mapping:
            - "募款" → admin_user_id_donation
            - "領頭雁" → admin_user_id_leader
            - "志工平台" → admin_user_id_volunteer
            - "心靈沉靜" → admin_user_id_mindpeace
            - "系統" → admin_user_id_system
            - Other/None → admin_user_id (default)
        """
        # Intent to config field mapping
        intent_mapping = {
            "募款": self.config.admin_user_id_donation,
            "領頭雁": self.config.admin_user_id_leader,
            "志工平台": self.config.admin_user_id_volunteer,
            "心靈沉靜": self.config.admin_user_id_mindpeace,
            "系統": self.config.admin_user_id_system,
        }

        # Get specific admin target for this intent
        if intent and intent in intent_mapping:
            target = intent_mapping[intent]
            if target:  # If configured
                logger.info(f"Routing notification to intent-specific admin: {intent}")
                return target
            else:
                logger.debug(f"Intent '{intent}' admin not configured, using default")

        # Fallback to default admin
        return self.config.admin_user_id

    def notify_admin(self, user_id: str, user_msg: str,
                    confidence: float = None,
                    ai_explanation: str = None,
                    notification_type: str = "handover",
                    ai_query: str = None,
                    intent: Optional[str] = None) -> None:
        """
        Notify admin about user interaction requiring attention.

        Args:
            user_id: User ID who sent the message
            user_msg: User's original message
            confidence: AI confidence score (if any)
            ai_explanation: AI's explanation (if any)
            notification_type: Type of notification (handover, new_user, media, ai_error)
            ai_query: AI query to use as keyword (if any)
            intent: AI-detected intent for routing to specific admin group
        """
        # Get appropriate admin target based on intent
        admin_target = self._get_admin_target_for_intent(intent)

        if not admin_target:
            logger.warning("No admin target configured for this intent, skipping notification")
            return

        try:
            # Get user nickname and organization name
            user_nickname = self.get_user_nickname(user_id)
            org_record = self.db.get_organization_record(user_id)
            org_name = org_record.get('organization_name', messages.get_organization_placeholder()) if org_record else messages.get_organization_placeholder()

            # Get notification title based on type
            title = messages.get_admin_notification_title(notification_type)

            # Use ai_query as keyword if provided, otherwise use title
            keyword = ai_query if ai_query else title
            notification_text = messages.format_admin_notification(
                user_nickname, org_name, user_msg, keyword, confidence
            )

            # Add intent information to notification if available
            if intent:
                notification_text += f"\n📌 分類: {intent}"

            # Push to specific admin target
            self._push_to_target(admin_target, notification_text)

            logger.info(f"Notified admin (intent: {intent or 'default'}) about user {user_nickname} ({notification_type})")

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
                source_type = "group" if hasattr(event.source, "group_id") and event.source.group_id else "room"
                source_id = event.source.group_id if source_type == "group" else event.source.room_id
                logger.info(f"Filtered out {source_type} message from {source_id}")
                return None
            
            message_type = type(event.message).__name__
            user_id = event.source.user_id

            # Skip stickers
            if message_type == "StickerMessageContent":
                logger.info(f"Skipped sticker from user {user_id}")
                return None

            # Handle text messages
            if hasattr(event.message, 'text'):
                user_input = event.message.text.strip()
                if not user_input:
                    return None

                return Message(
                    content=user_input,
                    user_id=user_id,
                    message_type="text",
                    reply_token=event.reply_token
                )

            # Everything else (media, unknown types) -> notify admin
            logger.info(f"Non-text message type '{message_type}' from user {user_id} - will notify admin")
            return Message(
                content=f"[{message_type}]",
                user_id=user_id,
                message_type="non_text",
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
        return messages.is_handover_request(message_text)