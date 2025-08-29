# src/services/agents_api_service.py
import asyncio
import json
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from agents import Agent, Runner, SQLiteSession, FileSearchTool, ModelSettings

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
    使用 OpenAI Agents SDK（JSON 結構化回覆版）：
    - Agent + SQLiteSession：自動保存多輪對話上下文
    - FileSearchTool：連結既有向量庫（如有設定 vector_store_id）
    - 解析 JSON 回覆並返回完整的 AIResponse 結構
    """

    def __init__(self, database_service: DatabaseService):
        self.config = config.openai
        self.db = database_service

        # OpenAI 官方 SDK（可做 vector store 等 REST 操作）
        self.client = OpenAI(api_key=self.config.api_key)

        self.model = self.config.model  # 例如 "gpt-4o"
        self.temperature = getattr(self.config, "temperature", 0.2)
        self.max_output_tokens = getattr(self.config, "max_tokens", 1024)
        self.vector_store_id = getattr(self.config, "vector_store_id", None)

        # 從 system_prompt.md 載入系統提示
        self.system_prompt = self._load_system_prompt()

        # 構建工具列（可選的 File Search）
        tools = []
        if self.vector_store_id:
            tools.append(
                FileSearchTool(
                    vector_store_ids=[self.vector_store_id],
                    max_num_results=5,  # 可調整以降低延遲/成本
                )
            )

        # 建立 Agent（生成參數放進 ModelSettings）
        self.agent = Agent(
            name="Simple Assistant",
            instructions=self.system_prompt,
            model=self.model,
            tools=tools,
            model_settings=ModelSettings(
                temperature=self.temperature,
                max_tokens=self.max_output_tokens,
            ),
        )

    def get_response(self, user_id: str, user_input: str) -> AIResponse:
        """
        以 Agents SDK 執行單輪（session 記憶會自動接上歷史）。
        傳入「單一字串」即可（不要 messages list）。
        """
        try:
            # 1) 建立/重用 Session（本地 SQLite）
            session = SQLiteSession(session_id=f"session:{user_id}")

            # 2) 如有使用者背景，前置到單一字串
            user_ctx = self._get_user_context(user_id)
            if user_ctx:
                turn_text = f"【使用者背景】\n{user_ctx}\n\n【問題】\n{user_input}"
            else:
                turn_text = user_input

            # 3) 執行（async 版 Runner.run；在當前執行緒建立/取得事件迴圈）
            async def _run_agent():
                return await Runner.run(self.agent, turn_text, session=session)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            result = loop.run_until_complete(_run_agent())

            # 4) 取得回覆並解析 JSON 結構
            response_text = getattr(result, "output_text", None) or str(result.final_output)
            if not response_text:
                response_text = str(result)

            # 嘗試解析 JSON 回覆
            parsed = self._parse_json_response(response_text, user_id)

            # 5) 落庫（沿用你的流程）
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
        return AIResponse(
            text=response_text,
            confidence=0.5,
            explanation="JSON解析失敗，使用原始回覆",
            user_id=user_id
        )

    def _load_system_prompt(self) -> str:
        """Load system prompt from system_prompt.md file."""
        try:
            with open('system_prompt.md', 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("system_prompt.md not found, using fallback prompt")
            return (
                "你是一位專業、友善且精簡的助理。"
                "回答時直截了當、語氣自然；若需要引用文件，先用提供的 File Search 工具檢索。"
            )
        except Exception as e:
            logger.error(f"Error loading system prompt: {e}")
            return (
                "你是一位專業、友善且精簡的助理。"
                "回答時直截了當、語氣自然；若需要引用文件，先用提供的 File Search 工具檢索。"
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
        For AgentsAPIService, context is handled automatically by session persistence.
        
        Args:
            user_id: User's LINE ID
            thread_id: Thread/Session ID (not used in Agents SDK but kept for interface compatibility)
        """
        try:
            user_context = self._get_user_context(user_id)
            if user_context:
                logger.info(f"User context refreshed for {user_id} (handled by session persistence)")
            else:
                logger.debug(f"No context to refresh for {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to refresh user context for {user_id}: {e}")
