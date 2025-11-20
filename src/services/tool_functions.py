"""
Tool functions that AI can call via OpenAI function calling.
These functions are registered in OpenAI platform and can be invoked by the AI model.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import json
from openai import OpenAI
from config import config
from src.utils import setup_logger

logger = setup_logger(__name__)


class ToolFunctions:
    """Collection of functions that AI can call via function calling."""

    def __init__(self):
        """Initialize with OpenAI client for calling small AI."""
        self.client = OpenAI(api_key=config.openai.api_key)

    @staticmethod
    def get_current_time(timezone_name: Optional[str] = "UTC") -> str:
        """
        Get current time in specified timezone.

        This function is useful when users ask about the current time or need
        to know what time it is now. Supports UTC and Taiwan timezone.

        Args:
            timezone_name: Timezone name. Options: "UTC" or "Asia/Taipei"
                          Defaults to "UTC" if not specified.

        Returns:
            str: Current time as formatted string with timezone info

        Examples:
            >>> ToolFunctions.get_current_time("UTC")
            "Current time: 2025-10-27 14:30:00 UTC"

            >>> ToolFunctions.get_current_time("Asia/Taipei")
            "Current time in Taiwan: 2025-10-27 22:30:00 (UTC+8)"
        """
        try:
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)

            if timezone_name == "UTC":
                time_str = now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
                return f"Current time: {time_str}"

            elif timezone_name == "Asia/Taipei":
                # Taiwan is UTC+8 (no daylight saving)
                taiwan_time = now_utc + timedelta(hours=8)
                time_str = taiwan_time.strftime('%Y-%m-%d %H:%M:%S')
                return f"Current time in Taiwan: {time_str} (UTC+8)"

            else:
                logger.warning(f"Unsupported timezone requested: {timezone_name}")
                return f"Timezone '{timezone_name}' not supported. Available timezones: UTC, Asia/Taipei"

        except Exception as e:
            logger.error(f"Error getting current time: {e}")
            return f"Error retrieving current time: {str(e)}"

    def ask_knowledge_expert(self, question: str, context: Optional[str] = None) -> str:
        """
        向「台灣一起夢想公益協會」知識專家（小 AI）詢問專業問題。

        當用戶詢問關於夢想協會的政策、服務、流程、FAQ 等專業問題時，
        大 AI 會呼叫此 function 向小 AI 請教專業知識。

        Args:
            question: 用戶的問題（關於夢想協會的專業問題）
            context: 額外的背景資訊，例如用戶的組織名稱、之前的對話內容等（可選）

        Returns:
            str: 小 AI 提供的專業答案（JSON 格式字串）

        Examples:
            >>> tools = ToolFunctions()
            >>> result = tools.ask_knowledge_expert(
            ...     question="微型社福補助需要什麼申請文件？",
            ...     context="用戶組織：財團法人XXX基金會"
            ... )
            >>> # Returns JSON with answer, confidence, sources, etc.
        """
        try:
            logger.info(f"[Knowledge Expert] Question: {question}")

            # Check if knowledge AI is configured
            if not config.openai.knowledge_ai_prompt_id:
                logger.warning("Knowledge AI prompt ID not configured")
                return json.dumps({
                    "answer": "抱歉，知識庫系統目前尚未設定。",
                    "confidence": 0.0,
                    "error": "KNOWLEDGE_AI_NOT_CONFIGURED"
                }, ensure_ascii=False)

            # 準備輸入給小 AI
            input_text = f"問題：{question}"
            if context:
                input_text += f"\n\n背景資訊：{context}"
                logger.info(f"[Knowledge Expert] Context: {context}")

            # 準備 prompt 參數（動態決定是否包含 version）
            prompt_params = {"id": config.openai.knowledge_ai_prompt_id}
            if config.openai.knowledge_ai_prompt_version:
                prompt_params["version"] = config.openai.knowledge_ai_prompt_version
                logger.info(f"[Knowledge Expert] Using version: {config.openai.knowledge_ai_prompt_version}")
            else:
                logger.info("[Knowledge Expert] Using latest version (auto-update)")

            # 呼叫小 AI (Responses API)
            logger.info("[Knowledge Expert] Calling small AI...")
            response = self.client.responses.create(
                prompt=prompt_params,
                input=input_text
            )

            # 取得小 AI 的回覆
            if hasattr(response, 'output_text'):
                result = response.output_text
            elif hasattr(response, 'content'):
                result = response.content
            else:
                result = str(response)

            logger.info(f"[Knowledge Expert] Response: {result[:200]}...")

            # Validate JSON format
            try:
                json.loads(result)  # Just validate, don't modify
                return result
            except json.JSONDecodeError:
                logger.warning("[Knowledge Expert] Response is not valid JSON, wrapping it")
                return json.dumps({
                    "answer": result,
                    "confidence": 0.7,
                    "note": "Response was not in JSON format"
                }, ensure_ascii=False)

        except Exception as e:
            logger.error(f"[Knowledge Expert] Error: {e}")
            return json.dumps({
                "answer": "抱歉，目前無法查詢相關資訊。請稍後再試或聯繫管理員。",
                "confidence": 0.0,
                "error": str(e)
            }, ensure_ascii=False)

    def check_submission_status(self, query: str) -> str:
        """
        檢查用戶的文件提交狀態或申請相關資訊。

        當用戶詢問關於文件提交、申請狀態、需要準備的文件、或申請流程相關問題時，
        大 AI 會呼叫此 function 查詢提交系統。

        Args:
            query: 用戶的查詢內容（純文字），例如：
                   - "我有提交過財務報表嗎？"
                   - "申請募款需要什麼文件？"
                   - "我的申請狀態如何？"

        Returns:
            str: 提交狀態或申請資訊說明（純文字）

        Examples:
            >>> tools = ToolFunctions()
            >>> result = tools.check_submission_status("我有提交過財務報表嗎？")
            >>> # Returns: "是的，您在2025-10-15提交過財務報表。狀態：已審核通過。"
        """
        try:
            logger.info(f"[Submission AI] Query: {query}")

            # Check if Submission AI is configured
            if not config.openai.submission_ai_prompt_id:
                logger.warning("Submission AI prompt ID not configured")
                return "抱歉，文件提交查詢系統目前尚未設定。請聯繫管理員。"

            # Prepare prompt params (dynamic version support like Knowledge AI)
            prompt_params = {"id": config.openai.submission_ai_prompt_id}
            if config.openai.submission_ai_prompt_version:
                prompt_params["version"] = config.openai.submission_ai_prompt_version
                logger.info(f"[Submission AI] Using version: {config.openai.submission_ai_prompt_version}")
            else:
                logger.info("[Submission AI] Using latest version (auto-update)")

            # Call Submission AI (simple string input)
            logger.info("[Submission AI] Calling Submission AI...")
            response = self.client.responses.create(
                prompt=prompt_params,
                input=query  # Just pass the query string directly
            )

            # Extract response text
            if hasattr(response, 'output_text'):
                result = response.output_text
            elif hasattr(response, 'content'):
                result = response.content
            else:
                result = str(response)

            logger.info(f"[Submission AI] Response: {result[:200]}...")

            return result

        except Exception as e:
            logger.error(f"[Submission AI] Error: {e}")
            return "抱歉，目前無法查詢提交狀態。請稍後再試或聯繫管理員。"
