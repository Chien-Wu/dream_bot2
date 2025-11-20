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

    def __init__(self, database_service: DatabaseService, line_service=None):
        self.config = config.openai
        self.line_service = line_service
        self.db = database_service

        # OpenAI 官方 SDK
        self.client = OpenAI(api_key=self.config.api_key)

        self.prompt_id = self.config.prompt_id
        self.prompt_version = self.config.prompt_version

        if not self.prompt_id:
            raise ValueError("OPENAI_PROMPT_ID must be set")

        # Initialize tool functions (needs to be instance for small AI calls)
        from src.services.tool_functions import ToolFunctions
        self.tool_functions = ToolFunctions()

    def get_response(self, user_id: str, user_input: str) -> AIResponse:
        """
        使用 OpenAI Prompt API 執行單輪對話。
        """
        try:
            input_text = user_input

            # 取得用戶上一輪回應ID
            last_response_id = self.db.get_user_thread_id(user_id)

            # 準備 prompt 參數（動態決定是否包含 version）
            prompt_params = {"id": self.prompt_id}
            if self.prompt_version:
                prompt_params["version"] = self.prompt_version
                logger.debug(f"Using prompt version: {self.prompt_version}")
            else:
                logger.debug("Using latest prompt version (auto-update)")

            # 準備API呼叫參數
            kwargs = {
                "prompt": prompt_params,
                "input": input_text
            }

            # 如果有上一輪對話，加入previous_response_id
            if last_response_id:
                kwargs["previous_response_id"] = last_response_id

            # 呼叫 Responses API
            response = self.client.responses.create(**kwargs)

            # 儲存此次回應ID供下次對話使用
            self.db.set_user_thread_id(user_id, response.id)

            # CHECK FOR FUNCTION CALLS
            function_calls = self._extract_function_calls(response)

            if function_calls:
                logger.info(f"Detected {len(function_calls)} function call(s)")
                # Handle function calls and get final response
                response = self._handle_function_calls(user_id, response, function_calls)
                # Update response ID after function calls
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
            # Re-raise all API errors so message processor can handle them as ai_error
            raise e

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
    
    def _extract_function_calls(self, response) -> list:
        """
        Extract function calls from OpenAI response.

        Args:
            response: OpenAI response object

        Returns:
            List of function call dictionaries with name, arguments, and call_id
        """
        function_calls = []

        try:
            if not hasattr(response, 'output') or not response.output:
                return function_calls

            for output_item in response.output:
                if hasattr(output_item, 'type') and output_item.type == "function_call":
                    function_calls.append({
                        "name": output_item.name,
                        "arguments": output_item.arguments,
                        "call_id": output_item.call_id
                    })
                    logger.info(f"Found function call: {output_item.name} with args: {output_item.arguments}")

        except Exception as e:
            logger.error(f"Error extracting function calls: {e}")

        return function_calls

    def _handle_function_calls(self, user_id: str, initial_response, function_calls: list):
        """
        Execute function calls and send results back to OpenAI.

        Args:
            user_id: User ID for context
            initial_response: Initial response containing function calls
            function_calls: List of function calls to execute

        Returns:
            Final response from OpenAI after function execution
        """
        try:
            # Execute each function and collect results
            function_results = []

            for func_call in function_calls:
                function_name = func_call["name"]
                arguments_str = func_call["arguments"]
                call_id = func_call["call_id"]

                logger.info(f"Executing function: {function_name}")
                logger.info(f"Arguments: {arguments_str}")

                # Execute the function
                result = self._execute_function(function_name, arguments_str)

                logger.info(f"Function result: {result}")

                # If debug mode is enabled, push small AI output to user
                if config.show_ai_debug_info:
                    if function_name == "ask_knowledge_expert":
                        self._push_small_ai_debug_info(user_id, arguments_str, result)
                    elif function_name == "check_submission_status":
                        self._push_submission_ai_debug_info(user_id, arguments_str, result)

                # Prepare result for OpenAI
                function_results.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result
                })

            # Send function results back to OpenAI to get final response
            logger.info("Sending function results back to OpenAI...")

            final_response = self.client.responses.create(
                prompt={
                    "id": self.prompt_id,
                    "version": self.prompt_version
                },
                input=function_results,
                previous_response_id=initial_response.id
            )

            logger.info("Received final response from OpenAI after function execution")

            return final_response

        except Exception as e:
            logger.error(f"Error handling function calls: {e}")
            raise e

    def _execute_function(self, function_name: str, arguments_str: str) -> str:
        """
        Execute a function by name with given arguments.

        Args:
            function_name: Name of the function to execute
            arguments_str: JSON string of arguments

        Returns:
            Function result as string
        """
        try:
            # Import tool functions
            from src.services.tool_functions import ToolFunctions
            import json

            # Parse arguments
            arguments = json.loads(arguments_str)

            # Map function names to actual functions
            function_map = {
                "get_current_time": ToolFunctions.get_current_time,  # Static method
                "ask_knowledge_expert": self.tool_functions.ask_knowledge_expert,  # Instance method (needs OpenAI client)
                "check_submission_status": self.tool_functions.check_submission_status,  # Instance method (needs OpenAI client)
            }

            if function_name not in function_map:
                error_msg = f"Unknown function: {function_name}"
                logger.error(error_msg)
                return error_msg

            # Execute the function
            func = function_map[function_name]
            result = func(**arguments)

            return result

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse function arguments: {e}"
            logger.error(error_msg)
            return error_msg

        except Exception as e:
            error_msg = f"Error executing function {function_name}: {e}"
            logger.error(error_msg)
            return error_msg

    def _push_small_ai_debug_info(self, user_id: str, arguments_str: str, result: str) -> None:
        """
        Push small AI debug information to LINE user when debug mode is enabled.

        Args:
            user_id: LINE user ID
            arguments_str: JSON string of function arguments
            result: Function result (small AI response)
        """
        try:
            # Skip if line_service not available
            if not self.line_service:
                logger.warning("LineService not available, skipping small AI debug info push")
                return

            import time

            # Parse arguments to get question
            arguments = json.loads(arguments_str)
            question = arguments.get("question", "")
            context = arguments.get("context", "")

            # Parse result to get small AI response
            try:
                result_json = json.loads(result)
                answer = result_json.get("answer", result)
                confidence = result_json.get("confidence", "N/A")
                sources = result_json.get("sources", [])
            except json.JSONDecodeError:
                answer = result
                confidence = "N/A"
                sources = []

            # Build debug message
            debug_msg = "🤖 小 AI (知識專家) 回覆：\n"
            debug_msg += "─" * 30 + "\n"
            debug_msg += f"📝 問題：{question}\n"
            if context:
                debug_msg += f"📌 背景：{context}\n"
            debug_msg += "\n💡 小 AI 答案：\n"
            debug_msg += f"{answer}\n"
            debug_msg += "\n" + "─" * 30 + "\n"
            debug_msg += f"🎯 信心度：{confidence}\n"
            if sources:
                debug_msg += f"📚 來源：{', '.join(sources)}\n"

            # Push message
            time.sleep(0.3)  # Small delay to ensure proper message order
            self.line_service.push_message(user_id, debug_msg)

            logger.info(f"Pushed small AI debug info to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to push small AI debug info: {e}")
            # Don't raise - debug info failure shouldn't break the main flow

    def _push_submission_ai_debug_info(self, user_id: str, arguments_str: str, result: str) -> None:
        """
        Push Submission AI debug information to LINE user when debug mode is enabled.

        Args:
            user_id: LINE user ID
            arguments_str: JSON string of function arguments
            result: Function result (Submission AI response)
        """
        try:
            # Skip if line_service not available
            if not self.line_service:
                logger.warning("LineService not available, skipping Submission AI debug info push")
                return

            import time

            # Parse arguments to get query
            arguments = json.loads(arguments_str)
            query = arguments.get("query", "")

            # Build debug message
            debug_msg = "🔍 Submission AI 回覆：\n"
            debug_msg += "─" * 30 + "\n"
            debug_msg += f"📝 查詢：{query}\n"
            debug_msg += "\n💬 Submission AI 回答：\n"
            debug_msg += f"{result}\n"
            debug_msg += "─" * 30

            # Push message
            time.sleep(0.3)  # Small delay to ensure proper message order
            self.line_service.push_message(user_id, debug_msg)

            logger.info(f"Pushed Submission AI debug info to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to push Submission AI debug info: {e}")
            # Don't raise - debug info failure shouldn't break the main flow

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

    
    

