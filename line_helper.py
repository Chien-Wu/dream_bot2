import logging

from linebot.v3.messaging import ReplyMessageRequest, MessagingApi, PushMessageRequest
from linebot.v3.messaging import TextMessage as LineTextMessage
from linebot.v3.webhook import MessageEvent

from buffer_manager import buffer_manager
from human_takeover import notify_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_line_message(event: MessageEvent, messaging_api: MessagingApi) -> None:
    try:
        if not hasattr(event.message, 'text'):
            logger.debug("忽略非文字訊息: %s", type(event.message))
            return
        
        user_input = event.message.text.strip()
        if not user_input:
            return
        
        if any(keyword in user_input.lower() for keyword in ["轉人工"]):
            notify_admin(
                messaging_api=messaging_api,
                user_id=event.source.user_id,
                user_msg=user_input,
                ai_reply="使用者主動要求轉人工"
            )
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[LineTextMessage(text="已為您通知管理者，請稍候。")]
                )
            )
            return
        
        buffer_manager.add_message(
            user_id=event.source.user_id,
            text=user_input,
            reply_token=event.reply_token,
            messaging_api=messaging_api
        )

    except Exception:
        logger.exception("處理 Line 訊息時發生錯誤")
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[LineTextMessage(text="系統發生錯誤，請稍後再試。")]
            )
        )
