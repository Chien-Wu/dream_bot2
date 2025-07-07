import logging

from linebot.v3.messaging import ReplyMessageRequest, MessagingApi, PushMessageRequest
from linebot.v3.messaging import TextMessage as LineTextMessage
from linebot.v3.webhook import MessageEvent

from buffer_manager import buffer_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_line_message(event: MessageEvent, messaging_api: MessagingApi) -> None:
    try:
        if not hasattr(event.message, 'text'):
            logger.debug("忽略非文字訊息: %s", type(event.message))
            return
        
        user_input = event.message.text.strip()
        if not user_input:
            logger.debug("忽略空文字訊息")
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
