"""
Internationalization messages module.
Contains all user-facing messages in different languages.
"""
from dataclasses import dataclass


@dataclass
class Messages:
    """Container for all user-facing messages."""

    # Admin notification titles
    ADMIN_NOTIFICATION_HANDOVER = "用戶需要人工協助"
    ADMIN_NOTIFICATION_NEW_USER = "新用戶加入"
    ADMIN_NOTIFICATION_MEDIA = "用戶傳送媒體檔案"
    ADMIN_NOTIFICATION_LOW_CONFIDENCE = "AI回覆信心度偏低"
    ADMIN_NOTIFICATION_AI_ERROR = "AI系統發生錯誤"
    ADMIN_NOTIFICATION_DEFAULT = "用戶需要人工協助"

    # Admin notification content
    ADMIN_NOTIFICATION_CONTACT = "聯絡人"
    ADMIN_NOTIFICATION_USER_MESSAGE = "用戶訊息"
    ADMIN_NOTIFICATION_KEYWORD = "關鍵字"
    ADMIN_NOTIFICATION_CONFIDENCE = "信心度"

    # Organization data
    ORGANIZATION_NOT_SET = "未設定"

    # User handover trigger
    USER_HANDOVER_TRIGGER = "轉人工"

    # User response messages
    HANDOVER_CONFIRMATION = "已為您通知管理者，請稍候。"

    # Chinese number patterns for text formatting
    CHINESE_NUMBERS = "一二三四五六七八九十"


class MessageManager:
    """Message manager for handling internationalization."""

    def __init__(self, language: str = "zh"):
        """Initialize message manager with default language."""
        self.language = language
        self.messages = Messages()

        # Future: Support for multiple languages
        # if language == "en":
        #     self.messages = EnglishMessages()
        # elif language == "zh":
        #     self.messages = Messages()  # Default Chinese

    def get_admin_notification_title(self, notification_type: str) -> str:
        """Get admin notification title by type."""
        titles = {
            "handover": self.messages.ADMIN_NOTIFICATION_HANDOVER,
            "new_user": self.messages.ADMIN_NOTIFICATION_NEW_USER,
            "media": self.messages.ADMIN_NOTIFICATION_MEDIA,
            "low_confidence": self.messages.ADMIN_NOTIFICATION_LOW_CONFIDENCE,
            "ai_error": self.messages.ADMIN_NOTIFICATION_AI_ERROR
        }
        return titles.get(notification_type, self.messages.ADMIN_NOTIFICATION_DEFAULT)

    def format_admin_notification(self, user_nickname: str, org_name: str,
                                 user_msg: str, keyword: str,
                                 confidence: float = None) -> str:
        """Format admin notification message."""
        notification_text = f"{self.messages.ADMIN_NOTIFICATION_CONTACT}: {user_nickname}({org_name})\n"
        notification_text += f"{self.messages.ADMIN_NOTIFICATION_USER_MESSAGE}: {user_msg}\n"
        notification_text += f"{self.messages.ADMIN_NOTIFICATION_KEYWORD}: {keyword}\n"

        if confidence is not None:
            notification_text += f"{self.messages.ADMIN_NOTIFICATION_CONFIDENCE}: {confidence:.2f}"

        return notification_text

    def is_handover_request(self, message_text: str) -> bool:
        """Check if message is a handover request."""
        return message_text.strip() == self.messages.USER_HANDOVER_TRIGGER

    def get_organization_placeholder(self) -> str:
        """Get organization name placeholder."""
        return self.messages.ORGANIZATION_NOT_SET

    def get_handover_confirmation(self) -> str:
        """Get handover confirmation message."""
        return self.messages.HANDOVER_CONFIRMATION


# Global message manager instance
messages = MessageManager()