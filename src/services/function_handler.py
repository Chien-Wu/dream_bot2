"""
Function handler for ChatGPT assistant function calls.
Defines and executes functions that the assistant can call.
"""
import json
import requests
import openai
from typing import Dict, Any, Callable, List
from datetime import datetime

from config import config
from src.utils import setup_logger
from src.services.database_service import DatabaseService
from src.services.line_service import LineService


logger = setup_logger(__name__)


class FunctionHandler:
    """Handler for ChatGPT assistant function calls."""
    
    def __init__(self, database_service: DatabaseService, line_service: LineService):
        self.db = database_service
        self.line = line_service
        self.functions = self._register_functions()
    
    def _register_functions(self) -> Dict[str, Callable]:
        """Register all available functions."""
        return {
            "get_user_organization_info": self._get_user_organization_info,
            "search_similar_organizations": self._search_similar_organizations,
            "get_user_conversation_history": self._get_user_conversation_history,
            "request_human_handover": self._request_human_handover,
            "get_current_datetime": self._get_current_datetime,
            "update_user_notes": self._update_user_notes,
            "update_organization_data": self._update_organization_data,
            "web_search": self._web_search
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get function definitions for the assistant."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_user_organization_info",
                    "description": "獲取用戶的組織基本資料，包括單位名稱、服務縣市、聯絡人資訊、服務對象等",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用戶的LINE ID"
                            }
                        },
                        "additionalProperties": False,
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_similar_organizations",
                    "description": "搜尋類似的組織或服務對象相同的組織",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_target": {
                                "type": "string",
                                "description": "服務對象",
                                "enum": ["弱勢兒少", "中年困境", "孤獨長者", "無助動物"]
                            },
                            "service_city": {
                                "type": "string",
                                "description": "服務縣市（可選）",
                                "enum": ["", "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市", "基隆市", "新竹市", "嘉義市", "宜蘭縣", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "台東縣", "花蓮縣", "澎湖縣", "金門縣", "連江縣"]
                            }
                        },
                        "additionalProperties": False,
                        "required": ["service_target", "service_city"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_conversation_history",
                    "description": "獲取用戶最近的對話記錄",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用戶的LINE ID"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回記錄數量，默認10",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10
                            }
                        },
                        "additionalProperties": False,
                        "required": ["user_id", "limit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "request_human_handover",
                    "description": "當用戶需要人工協助時，通知管理員",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用戶的LINE ID"
                            },
                            "reason": {
                                "type": "string",
                                "description": "需要人工協助的原因"
                            }
                        },
                        "additionalProperties": False,
                        "required": ["user_id", "reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_datetime",
                    "description": "獲取當前日期和時間",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_user_notes",
                    "description": "更新用戶的備註信息",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用戶的LINE ID"
                            },
                            "notes": {
                                "type": "string",
                                "description": "要添加的備註內容"
                            }
                        },
                        "additionalProperties": False,
                        "required": ["user_id", "notes"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_organization_data",
                    "description": "更新用戶的組織基本資料，如單位名稱、服務縣市等",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "用戶的LINE ID"
                            },
                            "organization_name": {
                                "type": "string",
                                "description": "新的單位名稱"
                            },
                            "service_city": {
                                "type": "string",
                                "description": "新的服務縣市",
                                "enum": ["", "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市", "基隆市", "新竹市", "嘉義市", "宜蘭縣", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "台東縣", "花蓮縣", "澎湖縣", "金門縣", "連江縣"]
                            },
                            "contact_info": {
                                "type": "string",
                                "description": "新的聯絡人資訊"
                            },
                            "service_target": {
                                "type": "string",
                                "description": "新的服務對象",
                                "enum": ["", "弱勢兒少", "中年困境", "孤獨長者", "無助動物"]
                            }
                        },
                        "additionalProperties": False,
                        "required": ["user_id", "organization_name", "service_city", "contact_info", "service_target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "搜尋網路上的最新資訊，包括新聞、政策、補助資訊等",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜尋關鍵字或問題"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "返回結果數量，默認5",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 5
                            }
                        },
                        "additionalProperties": False,
                        "required": ["query", "num_results"]
                    }
                }
            }
        ]
    
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call from the assistant.
        
        Args:
            function_name: Name of the function to call
            arguments: Function arguments
            
        Returns:
            Function result
        """
        try:
            if function_name not in self.functions:
                return {
                    "error": f"Unknown function: {function_name}"
                }
            
            logger.info(f"Executing function: {function_name} with args: {arguments}")
            
            # Call the function
            result = self.functions[function_name](**arguments)
            
            logger.info(f"Function {function_name} executed successfully")
            return {"result": result}
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": str(e)}
    
    def _get_user_organization_info(self, user_id: str) -> Dict[str, Any]:
        """Get user's organization information."""
        try:
            org_record = self.db.get_organization_record(user_id)
            
            if not org_record:
                return {"message": "用戶尚未提供組織資料"}
            
            return {
                "organization_name": org_record.get("organization_name"),
                "service_city": org_record.get("service_city"),
                "contact_info": org_record.get("contact_info"),
                "service_target": org_record.get("service_target"),
                "completion_status": org_record.get("completion_status"),
                "created_at": str(org_record.get("created_at", "")),
                "updated_at": str(org_record.get("updated_at", ""))
            }
            
        except Exception as e:
            return {"error": f"無法獲取組織資料: {str(e)}"}
    
    def _search_similar_organizations(self, service_target: str, service_city: str = "") -> Dict[str, Any]:
        """Search for similar organizations."""
        try:
            query = """
                SELECT organization_name, service_city, service_target, created_at
                FROM organization_data 
                WHERE completion_status = 'complete'
                AND service_target = %s
            """
            params = [service_target]
            
            if service_city and service_city.strip():
                query += " AND service_city = %s"
                params.append(service_city)
            
            query += " ORDER BY created_at DESC LIMIT 10"
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
            
            organizations = []
            for row in results:
                organizations.append({
                    "organization_name": row[0],
                    "service_city": row[1],
                    "service_target": row[2],
                    "created_at": str(row[3])
                })
            
            return {
                "found_count": len(organizations),
                "organizations": organizations
            }
            
        except Exception as e:
            return {"error": f"搜尋失敗: {str(e)}"}
    
    def _get_user_conversation_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get user's recent conversation history."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT content, ai_response, confidence, created_at
                    FROM message_history 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, limit))
                
                results = cursor.fetchall()
            
            history = []
            for row in results:
                history.append({
                    "user_message": row[0],
                    "ai_response": row[1],
                    "confidence": float(row[2]) if row[2] else None,
                    "timestamp": str(row[3])
                })
            
            return {
                "message_count": len(history),
                "history": history
            }
            
        except Exception as e:
            return {"error": f"無法獲取對話記錄: {str(e)}"}
    
    def _request_human_handover(self, user_id: str, reason: str) -> Dict[str, Any]:
        """Request human handover for the user."""
        try:
            # Notify admin
            self.line.notify_admin(
                user_id=user_id,
                user_msg=f"AI助手請求人工協助: {reason}",
                notification_type="handover"
            )
            
            return {
                "message": "已通知管理員，將有專人為您服務",
                "status": "handover_requested"
            }
            
        except Exception as e:
            return {"error": f"無法請求人工協助: {str(e)}"}
    
    def _get_current_datetime(self) -> Dict[str, Any]:
        """Get current date and time."""
        now = datetime.now()
        return {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
            "weekday_chinese": ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]
        }
    
    def _update_user_notes(self, user_id: str, notes: str) -> Dict[str, Any]:
        """Update user notes."""
        try:
            # For now, we'll add this to the organization record
            # You might want to create a separate notes table
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            note_entry = f"[{current_time}] {notes}"
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE organization_data 
                    SET raw_messages = CONCAT(COALESCE(raw_messages, ''), %s)
                    WHERE user_id = %s
                """, (f"\n{note_entry}", user_id))
                conn.commit()
            
            return {
                "message": "備註已更新",
                "note_added": note_entry
            }
            
        except Exception as e:
            return {"error": f"無法更新備註: {str(e)}"}
    
    def _update_organization_data(self, user_id: str, organization_name: str = "", 
                                service_city: str = "", contact_info: str = "", 
                                service_target: str = "") -> Dict[str, Any]:
        """Update user's organization data."""
        try:
            # Get current data first
            current_record = self.db.get_organization_record(user_id)
            if not current_record:
                return {"error": "用戶組織資料不存在"}
            
            # Prepare update data - only update non-empty fields
            update_fields = []
            params = []
            
            if organization_name and organization_name.strip():
                update_fields.append("organization_name = %s")
                params.append(organization_name.strip())
            
            if service_city and service_city.strip():
                update_fields.append("service_city = %s")
                params.append(service_city.strip())
            
            if contact_info and contact_info.strip():
                update_fields.append("contact_info = %s")
                params.append(contact_info.strip())
            
            if service_target and service_target.strip():
                update_fields.append("service_target = %s")
                params.append(service_target.strip())
            
            if not update_fields:
                return {"error": "沒有提供要更新的資料"}
            
            # Add updated timestamp
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            # Execute update
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                query = f"""
                    UPDATE organization_data 
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s
                """
                cursor.execute(query, params)
                conn.commit()
                
                if cursor.rowcount == 0:
                    return {"error": "沒有找到要更新的記錄"}
            
            # Get updated data to return
            updated_record = self.db.get_organization_record(user_id)
            
            return {
                "message": "組織資料已成功更新",
                "updated_data": {
                    "organization_name": updated_record.get("organization_name"),
                    "service_city": updated_record.get("service_city"),
                    "contact_info": updated_record.get("contact_info"),
                    "service_target": updated_record.get("service_target"),
                    "updated_at": str(updated_record.get("updated_at", ""))
                }
            }
            
        except Exception as e:
            return {"error": f"無法更新組織資料: {str(e)}"}
    
    def _web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform web search and analyze results with ChatGPT."""
        try:
            # Step 1: Perform web search using DuckDuckGo (free alternative)
            search_results = self._perform_search(query, num_results)
            
            if not search_results:
                return {"error": "沒有找到搜尋結果"}
            
            # Step 2: Use ChatGPT to analyze and summarize the search results
            analysis = self._analyze_search_results(query, search_results)
            
            return {
                "query": query,
                "summary": analysis,
                "sources": search_results,
                "total_results": len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"error": f"搜尋失敗: {str(e)}"}
    
    def _perform_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Perform web search using DuckDuckGo Instant Answer API."""
        try:
            # Use DuckDuckGo Instant Answer API (free, no API key required)
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Extract instant answer if available
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", "摘要"),
                    "snippet": data.get("Abstract", ""),
                    "url": data.get("AbstractURL", ""),
                    "source": data.get("AbstractSource", "DuckDuckGo")
                })
            
            # Extract related topics
            for topic in data.get("RelatedTopics", [])[:num_results-1]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("Text", "")[:100] + "...",
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo"
                    })
            
            # If no results from DuckDuckGo, try alternative search
            if not results:
                results = self._fallback_search(query, num_results)
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"Search API error: {e}")
            # Return fallback results
            return self._fallback_search(query, num_results)
    
    def _fallback_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Fallback search method when main search fails."""
        # This is a simple fallback - in production you might use other APIs
        return [{
            "title": f"搜尋建議: {query}",
            "snippet": f"建議您可以搜尋關於 '{query}' 的更多資訊。由於網路搜尋暫時無法使用，請嘗試直接搜尋相關的政府網站或官方資源。",
            "url": "",
            "source": "系統建議"
        }]
    
    def _analyze_search_results(self, query: str, search_results: List[Dict[str, str]]) -> str:
        """Use ChatGPT to analyze and summarize search results."""
        try:
            # Prepare content for analysis
            content = f"搜尋查詢: {query}\n\n搜尋結果:\n"
            for i, result in enumerate(search_results, 1):
                content += f"{i}. 標題: {result['title']}\n"
                content += f"   內容: {result['snippet']}\n"
                content += f"   來源: {result['source']}\n\n"
            
            # Use ChatGPT to analyze the results
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一個專業的資訊分析師，專門為台灣的社福組織提供資訊分析。請根據搜尋結果提供準確、有用的摘要，特別關注與社會福利、補助、政策相關的資訊。"
                    },
                    {
                        "role": "user", 
                        "content": f"請分析以下搜尋結果並提供簡潔的摘要：\n\n{content}\n\n請提供：\n1. 主要發現\n2. 重要資訊摘要\n3. 對社福組織的相關性"
                    }
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"ChatGPT analysis error: {e}")
            # Fallback to simple summary
            return self._simple_summary(query, search_results)
    
    def _simple_summary(self, query: str, search_results: List[Dict[str, str]]) -> str:
        """Simple fallback summary when ChatGPT analysis fails."""
        summary = f"關於 '{query}' 的搜尋結果摘要：\n\n"
        
        for i, result in enumerate(search_results, 1):
            summary += f"{i}. {result['title']}\n"
            if result['snippet']:
                summary += f"   {result['snippet'][:200]}...\n"
            summary += "\n"
        
        return summary