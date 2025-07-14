import os
import time
import logging
from typing import Optional, Callable

import openai
import thread_manager

try:
    from openai.error import OpenAIError
except ImportError:
    OpenAIError = Exception

from tools.messy_checker import is_messy
from tools.clean_ref import clean_references
from human_takeover import notify_admin
from tools.assistant_response import parse_assistant_response

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID", "")
MAX_POLL_RETRIES = int(os.getenv("OPENAI_POLL_MAX_RETRIES", "30"))
POLL_INTERVAL = float(os.getenv("OPENAI_POLL_INTERVAL", "1.0"))

if not OPENAI_API_KEY or not OPENAI_ASSISTANT_ID:
    raise RuntimeError("請先設定 OPENAI_API_KEY 與 OPENAI_ASSISTANT_ID 環境變數！")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AssistantClient:
    def __init__(self, assistant_id: str = OPENAI_ASSISTANT_ID) -> None:
        self.assistant_id = assistant_id

    def _get_or_create_thread(self, user_id: str) -> str:
        thread_id = thread_manager.get_thread_id(user_id)
        if thread_id:
            logger.debug(f"找到現有 thread_id for user {user_id}: {thread_id}")
            return thread_id
        logger.info(f"為 user {user_id} 建立新 thread")
        thread = openai.beta.threads.create()
        thread_manager.set_thread_id(user_id, thread.id)
        return thread.id

    def _send_user_message(self, thread_id: str, user_input: str) -> None:
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_input,
        )

    def _start_assistant_run(self, thread_id: str) -> str:
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id,
        )
        return run.id

    def _wait_for_run_completion(self, thread_id: str, run_id: str) -> bool:
        for attempt in range(MAX_POLL_RETRIES):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
            if run_status.status == "completed":
                return True
            time.sleep(POLL_INTERVAL)
        logger.warning(f"run {run_id} 等待超時 ({MAX_POLL_RETRIES} 次輪詢後仍未完成)")
        return False

    def _fetch_latest_assistant_reply(self, thread_id: str) -> Optional[str]:
        try:
            msgs = openai.beta.threads.messages.list(thread_id=thread_id).data
            assistant_msgs = [m for m in msgs if m.role == "assistant"]
            if not assistant_msgs:
                logger.error("在 thread 中沒有找到 assistant 訊息")
                return None
            last = assistant_msgs[0]
            content = last.content
            if content and hasattr(content[0], "text") and hasattr(content[0].text, "value"):
                return content[0].text.value
            logger.error("assistant 訊息格式不符合預期，無法擷取文字")
            return None
        except Exception as e:
            logger.exception("抓取 Assistant 回覆時發生例外")
            return None

    def get_assistant_reply(self, user_id: str, user_input: str) -> str:
        try:
            thread_id = self._get_or_create_thread(user_id)
            self._send_user_message(thread_id, user_input)
            run_id = self._start_assistant_run(thread_id)
            if not self._wait_for_run_completion(thread_id, run_id):
                return '{"text":"抱歉，AI 回應逾時，請稍後再試。","confidence":0}'
            reply = self._fetch_latest_assistant_reply(thread_id)
            if not reply:
                return '{"text":"抱歉，AI 無法取得回應內容，請稍後再試。","confidence":0}'
            if is_messy(reply):
                logger.error("assistant 回傳疑似亂碼或非預期內容：%s", reply)
                return '{"text":"抱歉，AI 回應內容異常，請稍後再試。","confidence":0}'
            return clean_references(reply)
        except OpenAIError:
            logger.exception("OpenAI API 呼叫失敗")
            return '{"text":"系統繁忙，請稍後再試。","confidence":0}'
        except Exception:
            logger.exception("處理 AI 回覆過程中發生未知錯誤")
            return '{"text":"系統錯誤，請稍後再試。","confidence":0}'

    def get_final_reply(
        self,
        user_id: str,
        user_input: str,
        messaging_api=None,
        notify_admin_func: Callable = notify_admin
    ) -> str:
        raw_reply = client.get_assistant_reply(user_id, user_input)
        text, confidence = parse_assistant_response(raw_reply)
        text = text + "(confidence"+str(confidence)+")"
        if confidence < 0.83:
            try:
                if messaging_api is not None:
                    notify_admin_func(
                        messaging_api=messaging_api,
                        user_id=user_id,
                        user_msg=user_input,
                        ai_reply=text,
                        confidence=confidence
                    )
                else:
                    logger.warning("通知管理員失敗：未提供 messaging_api 物件")
            except Exception:
                logger.exception("通知管理員時發生錯誤")
            return "此問題需要由專人處理，我們會請同仁盡快與您聯絡，謝謝您的提問！"
        else:
            return text if text else "抱歉，AI 暫無回應。"

    def reset_user_thread(self, user_id: str) -> bool:
        try:
            thread_manager.reset_thread_id(user_id)
            logger.info(f"已重設 user {user_id} 的 thread_id")
            return True
        except Exception:
            logger.exception(f"無法重設 user {user_id} 的 thread_id")
            return False


client = AssistantClient()

def get_assistant_reply(user_id: str, user_input: str) -> str:
    return client.get_assistant_reply(user_id, user_input)

def get_final_reply(
    user_id: str,
    user_input: str,
    messaging_api=None,
    notify_admin_func=notify_admin
) -> str:
    return client.get_final_reply(
        user_id=user_id,
        user_input=user_input,
        messaging_api=messaging_api,
        notify_admin_func=notify_admin_func
    )

def reset_user_thread(user_id: str) -> bool:
    return client.reset_user_thread(user_id)
