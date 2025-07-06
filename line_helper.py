import logging
from typing import List

from linebot.v3.messaging import MessagingApi, ReplyMessageRequest
from linebot.v3.messaging import TextMessage as LineTextMessage
from linebot.v3.webhook import MessageEvent

import assistant_helper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _split_text(text: str, max_len: int = 1000) -> List[str]:
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]

def handle_line_message(event: MessageEvent, messaging_api: MessagingApi) -> None:
    try:
        if not hasattr(event.message, 'text'):
            logger.debug("忽略非文字訊息: %s", type(event.message))
            return
        
        user_input = event.message.text.strip()
        if not user_input:
            logger.debug("忽略空文字訊息")
            return
        
        reply_text = assistant_helper.get_assistant_reply(
            user_id=event.source.user_id,
            user_input=user_input
        )
        
        if not reply_text:
            reply_text = "抱歉，AI 暫時沒有回應，請稍後再試！"
        
        for chunk in _split_text(reply_text):
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[LineTextMessage(text=chunk)]
                )
            )
    except Exception:
        logger.exception("處理 Line 訊息時發生錯誤")
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[LineTextMessage(text="系統發生錯誤，請稍後再試。")]
            )
        )
