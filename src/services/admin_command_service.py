"""
Simple admin command service for LINE Bot management.
"""
from typing import Dict, List, Any

from src.utils import setup_logger
from src.services.database_service import DatabaseService
from src.services.line_service import LineService

logger = setup_logger(__name__)

# Simple command registry
COMMANDS = {
    'user': {'desc': '查詢用戶詳細資訊', 'usage': '/user <用戶名稱或ID>'},
    'help': {'desc': '顯示所有可用指令', 'usage': '/help [指令名稱]'},
    'lowconf': {'desc': '查看低信心度問題', 'usage': '/lowconf [數量] [天數]'},
    'analyze': {'desc': 'AI分析失敗問題並提取重點', 'usage': '/analyze [天數] [最大問題數]'},
}


class AdminCommandService:
    """Simple admin command service."""
    
    def __init__(self, database_service: DatabaseService, line_service: LineService):
        self.db = database_service
        self.line = line_service
        from config import config
        self.confidence_threshold = config.openai.confidence_threshold
        
        logger.info("AdminCommandService initialized")
    
    def is_admin_command(self, message_content: str) -> bool:
        """Check if message is an admin command."""
        return message_content.strip().startswith('/')
    
    def execute_command(self, message_content: str) -> str:
        """Execute an admin command and return response message."""
        try:
            parts = message_content.strip()[1:].split()  # Remove / and split
            if not parts:
                return "❌ 請輸入指令名稱"
            
            command = parts[0].lower()
            args = parts[1:]
            
            # Direct command mapping
            if command == 'user':
                return self._handle_user_command(args)
            elif command == 'help':
                return self._handle_help_command(args)
            elif command == 'lowconf':
                return self._handle_low_confidence_command(args)
            elif command == 'analyze':
                return self._handle_analyze_command(args)
            else:
                return f"❌ 找不到指令 '{command}'\n使用 /help 查看所有可用指令"
                
        except Exception as e:
            logger.error(f"Error executing admin command: {e}")
            return f"❌ 執行指令時發生錯誤：{str(e)}"
    
    def _handle_help_command(self, args: List[str]) -> str:
        """Handle help command."""
        if args:
            command_name = args[0].lower()
            if command_name in COMMANDS:
                cmd = COMMANDS[command_name]
                return f"📖 指令說明\n\n**/{command_name}** - {cmd['desc']}\n用法：{cmd['usage']}"
            else:
                return f"❌ 找不到指令 '{command_name}'"
        
        # Show all commands (unique ones only)
        message = "🔧 管理員指令列表\n\n"
        unique_commands = {'user', 'help', 'lowconf', 'analyze'}
        
        for cmd in unique_commands:
            if cmd in COMMANDS:
                message += f"**/{cmd}** - {COMMANDS[cmd]['desc']}\n"
        
        message += "\n💡 使用 /help <指令名稱> 查看詳細說明"
        return message
    
    def _handle_user_command(self, args: List[str]) -> str:
        """Handle user lookup command."""
        if not args:
            return "❌ 請提供用戶名稱或ID\n用法：/user <用戶名稱或ID>"
        
        search_term = " ".join(args)
        
        try:
            users = self._search_users(search_term)
            
            if not users:
                return f"❌ 找不到匹配 '{search_term}' 的用戶"
            
            if len(users) == 1:
                return self._format_user_details(users[0])
            
            # Multiple users - show list
            message = f"👥 找到 {len(users)} 個匹配的用戶：\n\n"
            for i, user in enumerate(users[:10], 1):
                nickname = user.get('nickname', '未知')
                user_id_short = user['user_id'][-10:] if user['user_id'] else 'N/A'
                org_name = user.get('organization_name', '未設定')
                message += f"{i}. **{nickname}** ({user_id_short}) - {org_name}\n"
            
            if len(users) > 10:
                message += f"\n...還有 {len(users) - 10} 個結果"
            
            return message
            
        except Exception as e:
            logger.error(f"Error in user command: {e}")
            return f"❌ 查詢用戶時發生錯誤：{str(e)}"
    
    def _search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for users by ID, organization, or nickname."""
        try:
            query = """
                SELECT 
                    ut.user_id,
                    ut.thread_id,
                    ut.created_at,
                    ut.updated_at as last_seen,
                    od.organization_name,
                    od.service_city,
                    od.contact_info,
                    od.service_target,
                    od.completion_status,
                    (SELECT COUNT(*) FROM message_history mh WHERE mh.user_id = ut.user_id) as message_count,
                    (SELECT AVG(mh.confidence) FROM message_history mh WHERE mh.user_id = ut.user_id AND mh.confidence > 0) as avg_confidence
                FROM user_threads ut
                LEFT JOIN organization_data od ON ut.user_id = od.user_id
                WHERE 
                    ut.user_id LIKE %s OR 
                    od.organization_name LIKE %s OR
                    od.contact_info LIKE %s
                ORDER BY ut.created_at DESC
                LIMIT 20
            """
            
            search_pattern = f"%{search_term}%"
            results = self.db.execute_query(query, (search_pattern, search_pattern, search_pattern), fetch_all=True)
            
            # Add nicknames
            users = []
            for row in results:
                user_data = dict(row)
                user_data['nickname'] = self.line.get_user_nickname(user_data['user_id'])
                users.append(user_data)
            
            return users
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def _format_user_details(self, user: Dict[str, Any]) -> str:
        """Format user details for display."""
        nickname = user.get('nickname', '未知')
        user_id = user.get('user_id', 'N/A')
        message_count = user.get('message_count', 0)
        avg_confidence = user.get('avg_confidence')
        org_name = user.get('organization_name', '未設定')
        
        message = f"👤 **{nickname}**\n"
        message += f"ID: `{user_id}`\n"
        message += f"訊息數: {message_count}\n"
        
        if avg_confidence:
            confidence_emoji = "🟢" if avg_confidence >= 0.8 else "🟡" if avg_confidence >= 0.6 else "🔴"
            message += f"信心度: {confidence_emoji} {avg_confidence:.2f}\n"
        
        message += f"組織: {org_name}\n"
        
        if user.get('service_city'):
            message += f"服務縣市: {user['service_city']}\n"
        if user.get('contact_info'):
            message += f"聯絡資訊: {user['contact_info']}\n"
        
        return message
    
    def _handle_low_confidence_command(self, args: List[str]) -> str:
        """Handle low confidence questions lookup command."""
        try:
            limit = min(int(args[0]) if args else 10, 50)
            days = min(int(args[1]) if len(args) > 1 else 7, 30)
            
            query = """
                SELECT user_id, content, confidence, created_at
                FROM message_history 
                WHERE confidence < %s AND confidence > 0 
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY confidence ASC, created_at DESC
                LIMIT %s
            """
            
            results = self.db.execute_query(query, (self.confidence_threshold, days, limit), fetch_all=True)
            
            if not results:
                return f"✅ 過去 {days} 天內沒有找到低信心度問題"
            
            message = f"📊 低信心度問題 ({len(results)} 筆)\n\n"
            
            for i, row in enumerate(results, 1):
                user_id = row['user_id']
                nickname = self.line.get_user_nickname(user_id)
                confidence = row['confidence']
                question = row['content'][:80]
                
                confidence_emoji = "🔴" if confidence < 0.6 else "🟡"
                message += f"{i}. {confidence_emoji} **{nickname}** ({confidence:.2f})\n"
                message += f"   {question}...\n\n"
            
            return message
            
        except (ValueError, IndexError):
            return "❌ 用法：/lowconf [數量] [天數]"
        except Exception as e:
            logger.error(f"Error in low confidence command: {e}")
            return f"❌ 查詢失敗：{str(e)}"
    
    def _handle_analyze_command(self, args: List[str]) -> str:
        """Handle AI analysis of failed questions command."""
        try:
            days = min(int(args[0]) if args else 7, 30)
            max_questions = min(int(args[1]) if len(args) > 1 else 50, 100)
            
            # Get failed questions
            query = """
                SELECT content, COUNT(*) as frequency, MIN(confidence) as min_confidence
                FROM message_history 
                WHERE confidence < %s AND confidence > 0 
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                AND LENGTH(content) > 10
                GROUP BY content
                ORDER BY frequency DESC, min_confidence ASC
                LIMIT %s
            """
            
            results = self.db.execute_query(query, (self.confidence_threshold, days, max_questions), fetch_all=True)
            
            if not results:
                return f"✅ 過去 {days} 天內沒有需要分析的問題"
            
            # Simple analysis without external AI call
            message = f"📊 問題分析報告 ({len(results)} 筆)\n\n"
            message += "**常見失敗問題：**\n"
            
            for i, row in enumerate(results[:10], 1):
                content = row['content'][:100]
                frequency = row['frequency']
                message += f"{i}. [{frequency}次] {content}...\n"
            
            return message
            
        except (ValueError, IndexError):
            return "❌ 用法：/analyze [天數] [最大問題數]"
        except Exception as e:
            logger.error(f"Error in analyze command: {e}")
            return f"❌ 分析失敗：{str(e)}"
    
