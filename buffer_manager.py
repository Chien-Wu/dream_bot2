import threading
from typing import Dict

from linebot.v3.messaging import ReplyMessageRequest, MessagingApi, PushMessageRequest
from linebot.v3.messaging import TextMessage as LineTextMessage

import assistant_helper


def _split_text(text: str, max_len: int = 1000):
    return [text[i:i+max_len] for i in range(0, len(text), max_len)]


class BufferManager:
    def __init__(self, debounce_seconds: float = 1.0):
        self.debounce = debounce_seconds
        # 緩衝：user_id -> { text, reply_token, messaging_api, timer }
        self.buffers: Dict[str, Dict] = {}
        # 處理中狀態：user_id -> bool
        self.running: Dict[str, bool] = {}

    def add_message(
        self,
        user_id: str,
        text: str,
        reply_token: str,
        messaging_api: MessagingApi
    ) -> None:
        buf = self.buffers.get(user_id)
        if buf:
            buf["timer"].cancel()
            buf["text"] += "\n" + text
            buf["reply_token"] = reply_token
        else:
            buf = {
                "text": text,
                "reply_token": reply_token,
                "messaging_api": messaging_api,
            }
            self.buffers[user_id] = buf

        timer = threading.Timer(self.debounce, self.flush_buffer, args=[user_id])
        buf["timer"] = timer
        timer.start()

    def flush_buffer(self, user_id: str) -> None:
        buf = self.buffers.get(user_id)
        if not buf:
            return

        if self.running.get(user_id, False):
            timer = threading.Timer(self.debounce, self.flush_buffer, args=[user_id])
            buf["timer"] = timer
            timer.start()
            return

        self.running[user_id] = True
        buf = self.buffers.pop(user_id)

        full_text = buf["text"]
        reply_token = buf["reply_token"]
        messaging_api: MessagingApi = buf["messaging_api"]

        try:
            reply = assistant_helper.get_final_reply(user_id, full_text, messaging_api=messaging_api) or "抱歉，AI 暫無回應。"
            chunks = _split_text(reply)

            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[LineTextMessage(text=chunks[0])]
                )
            )
            for chunk in chunks[1:]:
                messaging_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[LineTextMessage(text=chunk)]
                    )
                )
        finally:
            self.running[user_id] = False


buffer_manager = BufferManager(debounce_seconds=10.0)
