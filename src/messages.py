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
    ADMIN_NOTIFICATION_ORG_REGISTERED = "用戶完成組織註冊"
    ADMIN_NOTIFICATION_DEFAULT = "用戶需要人工協助"

    # Admin notification content
    ADMIN_NOTIFICATION_CONTACT = "聯絡人"
    ADMIN_NOTIFICATION_USER_MESSAGE = "用戶訊息"
    ADMIN_NOTIFICATION_KEYWORD = "關鍵字"
    ADMIN_NOTIFICATION_CONFIDENCE = "信心度"

    # Organization data
    ORGANIZATION_NOT_SET = "未設定"

    # User handover trigger
    USER_HANDOVER_TRIGGER = ["轉真人", "轉人工", "找客服", "找專員", "專員", "客服", "真人"]

    # User response messages
    HANDOVER_CONFIRMATION = "已為您通知管理者，請稍候。"

    # Organization collection messages - NEW USERS (is_new = TRUE)
    ORG_REQUEST_MESSAGE_NEW = ["歡迎加入一起夢想！我是 AI 小助手，請先回覆【單位全名】，我會協助您的需求", "麻煩先提供【單位全名】，啟用AI客服功能", "請提供【單位全名】完成註冊，開始使用AI協助服務"]
    ORG_SUCCESS_MESSAGE_NEW = "已收到資料並完成建檔！很高興認識貴單位，一起夢想會持續支持微型社福，期待未來有更多交流 🤜🏻🤛🏻"

    # Organization collection messages - EXISTING USERS (is_new = FALSE)
    ORG_REQUEST_MESSAGE_EXISTING = ["您好，我是一起夢想 AI 小助手，請先回覆【單位全名】，我會再協助您的需求", "麻煩您先幫我回覆【單位全名】，我才能幫您處理或通知專人～", "請先回覆【單位全名】，啟用 AI 客服，避免重複提醒"]
    ORG_SUCCESS_MESSAGE_EXISTING = "已收到資料並完成建檔！"

    # Legacy messages (kept for backward compatibility)
    ORG_REQUEST_MESSAGE = ["您好，我是一起夢想 AI 小助手，請先回覆【單位全名】，我會再協助您的需求", "麻煩您先幫我回覆【單位全名】，我才能幫您處理或通知專人～", "請先回覆【單位全名】，啟用 AI 客服，避免重複提醒"]
    ORG_SUCCESS_MESSAGE = "已收到資料並完成建檔！"

    # System prompt for organization name extraction
    ORG_EXTRACTION_SYSTEM_PROMPT = """
你是社會福利機構名稱提取助手。
用戶會輸入組織名稱，可能包含：
- 全名（如「社團法人一起夢想公益協會」）
- 簡稱（如「一起夢想」「八方義行團」）
- 打字錯誤或缺字（如「一起夢相」「一其夢想」）
請務必遵守以下規則：
1. 若輸入字串明顯是組織名稱（即使未包含「協會」），且字數 ≥ 3，輸出該名稱。
2. 若輸入字串過短（2 字以下）或過於模糊（如「夢想」「一起」「協會」），輸出 “none”。
3. 若輸入包含多段文字，只取最像機構名稱的一段，不要組合無關文字。
4. 若字串含明顯組織類字（協會、協進會、促進會、讀書會、義行團、事務所等），即使拼字稍有錯誤也視為有效。
5. 輸出結果需為唯一名稱或 “none”，不得包含其他說明文字或標點符號。

"""

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
            "ai_error": self.messages.ADMIN_NOTIFICATION_AI_ERROR,
            "org_registered": self.messages.ADMIN_NOTIFICATION_ORG_REGISTERED
        }
        return titles.get(notification_type, self.messages.ADMIN_NOTIFICATION_DEFAULT)

    def format_admin_notification(self, user_nickname: str, org_name: str,
                                 user_msg: str, keyword: str,
                                 confidence: float = None) -> str:
        """Format admin notification message."""
        notification_text = f"{self.messages.ADMIN_NOTIFICATION_CONTACT}: {org_name}({user_nickname})\n"
        notification_text += f"{self.messages.ADMIN_NOTIFICATION_USER_MESSAGE}: {user_msg}\n"
        notification_text += f"{self.messages.ADMIN_NOTIFICATION_KEYWORD}: {keyword}\n"

        if confidence is not None:
            notification_text += f"{self.messages.ADMIN_NOTIFICATION_CONFIDENCE}: {confidence:.2f}"

        return notification_text

    def is_handover_request(self, message_text: str) -> bool:
        """Check if message is a handover request."""
        if not message_text:
            return False

        message_lower = message_text.lower().strip()

        # Check if any trigger phrase appears in the message (case-insensitive)
        for trigger in self.messages.USER_HANDOVER_TRIGGER:
            if trigger.lower() in message_lower:
                return True

        # Special handling for "人工" - only trigger if not part of "人工智慧" or similar compounds
        if "人工" in message_lower:
            # Exclude common false positives
            false_positives = ["人工智慧", "人工智能", "人工費", "人工成本"]
            if not any(fp in message_lower for fp in false_positives):
                return True

        return False

    def get_organization_placeholder(self) -> str:
        """Get organization name placeholder."""
        return self.messages.ORGANIZATION_NOT_SET

    def get_handover_confirmation(self) -> str:
        """Get handover confirmation message."""
        return self.messages.HANDOVER_CONFIRMATION

    def get_org_request_message(self, attempt_count: int = 0, is_new_user: bool = None) -> str:
        """Get organization name request message based on attempt count and user type."""
        if is_new_user:  # Truthy check (handles True, 1, etc.)
            messages_list = self.messages.ORG_REQUEST_MESSAGE_NEW
        elif is_new_user is not None and not is_new_user:  # Falsy but not None (handles False, 0, etc.)
            messages_list = self.messages.ORG_REQUEST_MESSAGE_EXISTING
        else:
            # Fallback to legacy messages if is_new_user is None (backward compatibility)
            messages_list = self.messages.ORG_REQUEST_MESSAGE

        # Use the attempt count as index, but cap at the last message
        index = min(attempt_count, len(messages_list) - 1)
        return messages_list[index]

    def get_org_success_message(self, is_new_user: bool = None) -> str:
        """Get organization name success message based on user type."""
        if is_new_user:  # Truthy check (handles True, 1, etc.)
            return self.messages.ORG_SUCCESS_MESSAGE_NEW
        elif is_new_user is not None and not is_new_user:  # Falsy but not None (handles False, 0, etc.)
            return self.messages.ORG_SUCCESS_MESSAGE_EXISTING
        else:
            # Fallback to legacy message if is_new_user is None (backward compatibility)
            return self.messages.ORG_SUCCESS_MESSAGE

    def get_org_extraction_prompt(self) -> str:
        """Get organization name extraction system prompt."""
        return self.messages.ORG_EXTRACTION_SYSTEM_PROMPT


# Global message manager instance
messages = MessageManager()