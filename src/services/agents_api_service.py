# src/services/agents_api_service.py
import json
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from config import config
from src.utils import setup_logger
from src.models import AIResponse
from src.services.database_service import DatabaseService

logger = setup_logger(__name__)


@dataclass
class ConversationMessage:
    role: str  # 'system', 'user', 'assistant'
    content: str


class AgentsAPIService:
    """
    使用 OpenAI Prompt API 進行回覆：
    - responses.create() 搭配 prompt ID
    - 解析 JSON 回覆並返回完整的 AIResponse 結構
    """

    def __init__(self, database_service: DatabaseService):
        self.config = config.openai
        self.db = database_service

        # OpenAI 官方 SDK
        self.client = OpenAI(api_key=self.config.api_key)

        self.prompt_id = self.config.prompt_id
        self.prompt_version = self.config.prompt_version
        
        if not self.prompt_id:
            raise ValueError("OPENAI_PROMPT_ID must be set")

    def get_response(self, user_id: str, user_input: str) -> AIResponse:
        """
        使用 OpenAI Prompt API 執行單輪對話。
        """
        try:
            # 如有使用者背景，前置到單一字串
            user_ctx = self._get_user_context(user_id)
            if user_ctx:
                input_text = f"【使用者背景】\n{user_ctx}\n\n【問題】\n{user_input}"
            else:
                input_text = user_input

            # 取得用戶上一輪回應ID
            last_response_id = self.db.get_user_thread_id(user_id)
            
            # 準備API呼叫參數
            kwargs = {
                "prompt": {
                    "id": self.prompt_id,
                    "version": self.prompt_version
                },
                "input": input_text
            }
            
            # 如果有上一輪對話，加入previous_response_id
            if last_response_id:
                kwargs["previous_response_id"] = last_response_id
            
            # 使用 responses.create 呼叫 prompt ID
            response = self.client.responses.create(**kwargs)
            
            # 儲存此次回應ID供下次對話使用
            self.db.set_user_thread_id(user_id, response.id)

            # 取得回覆文字
            if hasattr(response, 'output_text'):
                response_text = response.output_text
            elif hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)

            # 解析 JSON 回覆
            parsed = self._parse_json_response(response_text, user_id)

            # 落庫
            message_history_id = self.db.log_message(
                user_id=user_id,
                content=user_input,
                ai_response=parsed.text,
                ai_explanation=parsed.explanation,
                confidence=parsed.confidence,
            )
            if message_history_id:
                self.db.save_ai_detail(message_history_id, parsed)

            return parsed

        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            return AIResponse(
                text="抱歉，AI 服務暫時無法回應，請稍後再試。",
                confidence=0.0,
                explanation=f"Error: {str(e)}",
                user_id=user_id,
            )

    # ===== 輔助 =====
    def _parse_json_response(self, response_text: str, user_id: str) -> AIResponse:
        """Parse JSON response from the agent."""
        try:
            # 清理回覆文字，移除可能的前後文字或Markdown
            response_text = response_text.strip()
            
            # 尋找 JSON 部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning(f"No JSON found in response: {response_text[:200]}")
                return self._create_fallback_response(response_text, user_id)
            
            json_str = response_text[start_idx:end_idx + 1]
            parsed_json = json.loads(json_str)
            
            # 創建 AIResponse 對象
            return AIResponse(
                text=parsed_json.get("text", ""),
                confidence=float(parsed_json.get("confidence", 0.0)),
                explanation=parsed_json.get("explanation"),
                user_id=user_id,
                intent=parsed_json.get("intent"),
                queries=parsed_json.get("queries", []),
                sources=parsed_json.get("sources", []),
                gaps=parsed_json.get("gaps", []),
                policy_scope=parsed_json.get("policy", {}).get("scope"),
                policy_risk=parsed_json.get("policy", {}).get("risk"),
                policy_pii=parsed_json.get("policy", {}).get("pii"),
                policy_escalation=parsed_json.get("policy", {}).get("escalation"),
                notes=parsed_json.get("notes")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}, response: {response_text[:500]}")
            return self._create_fallback_response(response_text, user_id)
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return self._create_fallback_response(response_text, user_id)
    
    def _create_fallback_response(self, response_text: str, user_id: str) -> AIResponse:
        """Create fallback response when JSON parsing fails."""
        # Try to extract partial data from truncated JSON
        confidence = 0.5
        text = response_text
        explanation = "JSON解析失敗，使用原始回覆"
        
        try:
            # Extract confidence if available in truncated response
            import re
            confidence_match = re.search(r'"confidence":\s*([\d.]+)', response_text)
            if confidence_match:
                confidence = float(confidence_match.group(1))
                logger.info(f"Extracted confidence {confidence} from partial JSON")
            
            # Extract text if available 
            text_match = re.search(r'"text":\s*"([^"]*)"', response_text)
            if text_match:
                text = text_match.group(1)
                logger.info("Extracted text from partial JSON")
                
        except Exception as e:
            logger.error(f"Failed to extract partial data from response: {e}")
        
        return AIResponse(
            text=text,
            confidence=confidence,
            explanation=explanation,
            user_id=user_id
        )

    
    def _get_user_context(self, user_id: str) -> str:
        try:
            org_record = self.db.get_organization_record(user_id)
            if not org_record or org_record.get("completion_status") != "complete":
                return ""
            parts = []
            if org_record.get("organization_name"):
                parts.append(f"單位全名：{org_record['organization_name']}")
            if org_record.get("service_city"):
                parts.append(f"服務縣市：{org_record['service_city']}")
            if org_record.get("contact_info"):
                parts.append(f"聯絡人資訊：{org_record['contact_info']}")
            if org_record.get("service_target"):
                parts.append(f"服務對象：{org_record['service_target']}")
            return "\n".join(parts) if parts else ""
        except Exception as e:
            logger.error(f"Failed to get user context for {user_id}: {e}")
            return ""
    

    def _refresh_user_context(self, user_id: str, thread_id: str) -> None:
        """
        Refresh user context in existing session.
        For Prompt API, context is handled per-request.
        
        Args:
            user_id: User's LINE ID
            thread_id: Thread/Session ID (not used in Prompt API but kept for interface compatibility)
        """
        try:
            user_context = self._get_user_context(user_id)
            if user_context:
                logger.info(f"User context refreshed for {user_id}")
            else:
                logger.debug(f"No context to refresh for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to refresh user context for {user_id}: {e}")
