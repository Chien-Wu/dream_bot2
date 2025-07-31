"""
Professional admin command service for LINE Bot management.
Provides modular, extensible command system for administrative tasks.
"""
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

from src.utils import setup_logger
from src.services.database_service import DatabaseService
from src.services.line_service import LineService


logger = setup_logger(__name__)


@dataclass
class CommandResult:
    """Result of an admin command execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class CommandInfo:
    """Information about a command."""
    name: str
    description: str
    usage: str
    handler: Callable
    aliases: List[str] = None


class AdminCommandService:
    """
    Professional admin command service with modular architecture.
    
    Features:
    - Command registration system
    - Fuzzy matching for user-friendly input
    - Extensible handler system
    - Professional response formatting
    - Error handling and validation
    """
    
    def __init__(self, database_service: DatabaseService, line_service: LineService):
        self.db = database_service
        self.line = line_service
        self.commands: Dict[str, CommandInfo] = {}
        
        logger.info(f"AdminCommandService initializing with ID: {id(self)}")
        self._register_default_commands()
        logger.info(f"AdminCommandService initialized with {len(self.commands)} commands: {list(self.commands.keys())}")
    
    def _register_default_commands(self) -> None:
        """Register default admin commands."""
        self.register_command(
            name="user",
            description="查詢用戶詳細資訊",
            usage="/user <用戶名稱或ID>",
            handler=self._handle_user_command,
            aliases=["u", "用戶", "使用者"]
        )
        
        self.register_command(
            name="help",
            description="顯示所有可用指令",
            usage="/help [指令名稱]",
            handler=self._handle_help_command,
            aliases=["h", "?", "幫助"]
        )
    
    def register_command(self, name: str, description: str, usage: str, 
                        handler: Callable, aliases: List[str] = None) -> None:
        """
        Register a new admin command.
        
        Args:
            name: Command name (without /)
            description: Command description
            usage: Usage example
            handler: Function to handle the command
            aliases: Alternative names for the command
        """
        command_info = CommandInfo(
            name=name,
            description=description,
            usage=usage,
            handler=handler,
            aliases=aliases or []
        )
        
        # Register main command
        self.commands[name] = command_info
        
        # Register aliases
        for alias in (aliases or []):
            self.commands[alias] = command_info
        
        logger.info(f"Registered admin command: {name} (aliases: {aliases})")
    
    def is_admin_command(self, message_content: str) -> bool:
        """Check if message is an admin command."""
        return message_content.strip().startswith('/')
    
    def parse_command(self, message_content: str) -> tuple[str, List[str]]:
        """
        Parse command and arguments from message.
        
        Args:
            message_content: Raw message content
            
        Returns:
            Tuple of (command_name, arguments_list)
        """
        # Remove leading / and split by spaces
        content = message_content.strip()[1:]  # Remove /
        parts = content.split()
        
        if not parts:
            return "", []
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    def execute_command(self, command: str, args: List[str]) -> CommandResult:
        """
        Execute an admin command.
        
        Args:
            command: Command name
            args: Command arguments
            
        Returns:
            CommandResult with execution results
        """
        try:
            # Find command (exact match or alias)
            command_info = self.commands.get(command.lower())
            
            if not command_info:
                # Try fuzzy matching
                suggestions = self._find_similar_commands(command)
                if suggestions:
                    suggestion_text = "、".join(suggestions[:3])
                    return CommandResult(
                        success=False,
                        message=f"❌ 找不到指令 '{command}'\n\n💡 您是否要找：{suggestion_text}",
                        error=f"Command '{command}' not found"
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"❌ 找不到指令 '{command}'\n使用 /help 查看所有可用指令",
                        error=f"Command '{command}' not found"
                    )
            
            # Execute command handler
            logger.info(f"Executing admin command: {command} with args: {args}")
            return command_info.handler(args)
            
        except Exception as e:
            logger.error(f"Error executing admin command '{command}': {e}")
            return CommandResult(
                success=False,
                message=f"❌ 執行指令時發生錯誤\n{str(e)}",
                error=str(e)
            )
    
    def _find_similar_commands(self, command: str) -> List[str]:
        """Find similar commands using fuzzy matching."""
        command_lower = command.lower()
        matches = []
        
        for cmd_name in self.commands.keys():
            # Simple similarity check
            if command_lower in cmd_name or cmd_name in command_lower:
                matches.append(f"/{cmd_name}")
            elif self._levenshtein_distance(command_lower, cmd_name) <= 2:
                matches.append(f"/{cmd_name}")
        
        return list(set(matches))  # Remove duplicates
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    # Command Handlers
    
    def _handle_help_command(self, args: List[str]) -> CommandResult:
        """Handle help command."""
        if args and args[0]:
            # Show specific command help
            command_name = args[0].lower()
            command_info = self.commands.get(command_name)
            
            if not command_info:
                return CommandResult(
                    success=False,
                    message=f"❌ 找不到指令 '{command_name}'"
                )
            
            message = f"📖 指令說明\n\n"
            message += f"**{command_info.name}** - {command_info.description}\n"
            message += f"用法：{command_info.usage}\n"
            if command_info.aliases:
                aliases_text = "、".join([f"/{alias}" for alias in command_info.aliases])
                message += f"別名：{aliases_text}"
            
            return CommandResult(success=True, message=message)
        
        # Show all commands
        message = "🔧 管理員指令列表\n\n"
        
        # Group commands by main name (avoid showing aliases)
        seen_commands = set()
        for cmd_info in self.commands.values():
            if cmd_info.name not in seen_commands:
                seen_commands.add(cmd_info.name)
                message += f"**/{cmd_info.name}** - {cmd_info.description}\n"
        
        message += "\n💡 使用 /help <指令名稱> 查看詳細說明"
        
        return CommandResult(success=True, message=message)
    
    def _handle_user_command(self, args: List[str]) -> CommandResult:
        """Handle user lookup command."""
        if not args:
            return CommandResult(
                success=False,
                message="❌ 請提供用戶名稱或ID\n用法：/user <用戶名稱或ID>"
            )
        
        search_term = " ".join(args)
        
        try:
            # Search for users
            users = self._search_users(search_term)
            
            if not users:
                return CommandResult(
                    success=False,
                    message=f"❌ 找不到匹配 '{search_term}' 的用戶"
                )
            
            if len(users) == 1:
                # Single user - show detailed info
                user = users[0]
                message = self._format_user_details(user)
                return CommandResult(success=True, message=message, data={"user": user})
            
            # Multiple users - show list
            message = f"👥 找到 {len(users)} 個匹配的用戶：\n\n"
            for i, user in enumerate(users[:10], 1):  # Limit to 10 results
                nickname = user.get('nickname', '未知')
                user_id_short = user['user_id'][-10:] if user['user_id'] else 'N/A'
                org_name = user.get('organization_name', '未設定')
                message += f"{i}. **{nickname}** ({user_id_short})\n"
                message += f"   組織：{org_name}\n"
            
            if len(users) > 10:
                message += f"\n...還有 {len(users) - 10} 個結果\n"
            
            message += "\n💡 使用完整用戶名稱或ID查看詳細資訊"
            
            return CommandResult(success=True, message=message, data={"users": users})
            
        except Exception as e:
            logger.error(f"Error in user command: {e}")
            return CommandResult(
                success=False,
                message=f"❌ 查詢用戶時發生錯誤：{str(e)}",
                error=str(e)
            )
    
    def _search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for users by ID or organization.
        
        Args:
            search_term: Search query
            
        Returns:
            List of matching user records
        """
        try:
            # First, try to get user by exact ID match
            if search_term.startswith('U') and len(search_term) > 10:
                user_data = self._get_user_by_id(search_term)
                if user_data:
                    return [user_data]
            
            # Search in database using actual table schema
            query = """
                SELECT DISTINCT
                    ut.user_id,
                    ut.thread_id,
                    ut.created_at,
                    od.organization_name,
                    od.service_city,
                    od.contact_info,
                    od.service_target,
                    od.completion_status,
                    od.created_at as org_created_at,
                    (SELECT COUNT(*) FROM message_history mh WHERE mh.user_id = ut.user_id) as message_count,
                    (SELECT AVG(mh.confidence) FROM message_history mh WHERE mh.user_id = ut.user_id AND mh.confidence > 0) as avg_confidence,
                    (SELECT MAX(mh.created_at) FROM message_history mh WHERE mh.user_id = ut.user_id) as last_message_time
                FROM user_threads ut
                LEFT JOIN organization_data od ON ut.user_id = od.user_id
                WHERE 
                    ut.user_id LIKE %s OR 
                    od.organization_name LIKE %s OR
                    od.contact_info LIKE %s
                ORDER BY last_message_time DESC, ut.created_at DESC
                LIMIT 20
            """
            
            search_pattern = f"%{search_term}%"
            results = self.db.execute_query(
                query, 
                (search_pattern, search_pattern, search_pattern),
                fetch_all=True
            )
            
            # Enrich results with nicknames from LINE API
            enriched_results = []
            for row in results:
                user_data = dict(row)
                user_data['nickname'] = self.line.get_user_nickname(user_data['user_id'])
                enriched_results.append(user_data)
            
            # If no results found by database search, try searching by nickname
            if not enriched_results and not search_term.startswith('U'):
                enriched_results = self._search_by_nickname(search_term)
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            return []
    
    def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by exact ID match."""
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
                    od.created_at as org_created_at,
                    (SELECT COUNT(*) FROM message_history mh WHERE mh.user_id = ut.user_id) as message_count,
                    (SELECT AVG(mh.confidence) FROM message_history mh WHERE mh.user_id = ut.user_id AND mh.confidence > 0) as avg_confidence,
                    (SELECT MAX(mh.created_at) FROM message_history mh WHERE mh.user_id = ut.user_id) as last_message_time
                FROM user_threads ut
                LEFT JOIN organization_data od ON ut.user_id = od.user_id
                WHERE ut.user_id = %s
            """
            
            result = self.db.execute_query(query, (user_id,), fetch_one=True)
            if result:
                user_data = dict(result)
                # Enrich with nickname from LINE API
                user_data['nickname'] = self.line.get_user_nickname(user_data['user_id'])
                return user_data
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def _search_by_nickname(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search users by nickname (requires fetching all users and checking nicknames).
        This is less efficient but necessary since nicknames are not stored in DB.
        """
        try:
            # Get all users with recent activity (limit to avoid performance issues)
            query = """
                SELECT DISTINCT
                    ut.user_id,
                    ut.thread_id,
                    ut.created_at,
                    od.organization_name,
                    od.service_city,
                    od.contact_info,
                    od.service_target,
                    od.completion_status,
                    od.created_at as org_created_at,
                    (SELECT COUNT(*) FROM message_history mh WHERE mh.user_id = ut.user_id) as message_count,
                    (SELECT AVG(mh.confidence) FROM message_history mh WHERE mh.user_id = ut.user_id AND mh.confidence > 0) as avg_confidence,
                    (SELECT MAX(mh.created_at) FROM message_history mh WHERE mh.user_id = ut.user_id) as last_message_time
                FROM user_threads ut
                LEFT JOIN organization_data od ON ut.user_id = od.user_id
                WHERE ut.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY last_message_time DESC, ut.created_at DESC
                LIMIT 50
            """
            
            results = self.db.execute_query(query, fetch_all=True)
            matching_users = []
            
            # Check each user's nickname
            for row in results:
                user_data = dict(row)
                nickname = self.line.get_user_nickname(user_data['user_id'])
                user_data['nickname'] = nickname
                
                # Check if nickname contains search term (case insensitive)
                if search_term.lower() in nickname.lower():
                    matching_users.append(user_data)
            
            return matching_users
            
        except Exception as e:
            logger.error(f"Error searching by nickname: {e}")
            return []
    
    def _format_user_details(self, user: Dict[str, Any]) -> str:
        """Format user details for display."""
        message = "👤 用戶詳細資訊\n\n"
        
        # Basic info
        nickname = user.get('nickname', '未知')
        user_id = user.get('user_id', 'N/A')
        
        message += f"**姓名：** {nickname}\n"
        message += f"**用戶ID：** `{user_id}`\n"
        
        # Timestamps
        if user.get('created_at'):
            created_at = user['created_at'].strftime('%Y-%m-%d %H:%M') if hasattr(user['created_at'], 'strftime') else str(user['created_at'])
            message += f"**加入時間：** {created_at}\n"
        
        if user.get('last_seen'):
            last_seen = user['last_seen'].strftime('%Y-%m-%d %H:%M') if hasattr(user['last_seen'], 'strftime') else str(user['last_seen'])
            message += f"**最後活動：** {last_seen}\n"
        
        # Activity stats
        message_count = user.get('message_count', 0)
        avg_confidence = user.get('avg_confidence')
        message += f"**訊息數量：** {message_count}\n"
        
        if avg_confidence:
            confidence_emoji = "🟢" if avg_confidence >= 0.8 else "🟡" if avg_confidence >= 0.6 else "🔴"
            message += f"**平均信心度：** {confidence_emoji} {avg_confidence:.2f}\n"
        
        # Organization info
        message += "\n📋 **組織資訊**\n"
        
        org_name = user.get('organization_name')
        if org_name:
            message += f"**組織名稱：** {org_name}\n"
            
            service_city = user.get('service_city')
            if service_city:
                message += f"**服務縣市：** {service_city}\n"
            
            contact_info = user.get('contact_info')
            if contact_info:
                message += f"**聯絡資訊：** {contact_info}\n"
            
            service_target = user.get('service_target')
            if service_target:
                message += f"**服務對象：** {service_target}\n"
            
            completion_status = user.get('completion_status', 'incomplete')
            status_emoji = "✅" if completion_status == 'complete' else "⏳"
            status_text = "已完成" if completion_status == 'complete' else "進行中"
            message += f"**建檔狀態：** {status_emoji} {status_text}\n"
        else:
            message += "尚未建立組織資料\n"
        
        return message