"""
Function handler for ChatGPT assistant function calls.
Defines and executes functions that the assistant can call.
"""
from typing import Dict, Any, Callable, List
from datetime import datetime

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
            "get_current_datetime": self._get_current_datetime,
            "request_human_handover": self._request_human_handover
        }
    
    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get function definitions for the assistant."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_user_organization_info",
                    "description": "獲取用戶的組織基本資料，包括單位全名、服務縣市、聯絡人資訊、服務對象等",
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
    
