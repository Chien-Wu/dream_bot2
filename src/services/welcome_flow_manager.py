"""
Welcome Flow Manager for handling new user onboarding and organization data collection.
"""
from typing import Dict, Optional
from dataclasses import dataclass

from src.services.organization_analyzer import OrganizationDataAnalyzer, OrganizationData
from src.services.database_service import DatabaseService
from src.services.line_service import LineService
from src.utils import setup_logger


logger = setup_logger(__name__)


@dataclass
class WelcomeFlowResult:
    """Result of welcome flow processing."""
    should_block: bool
    response_message: Optional[str] = None
    notify_admin: bool = False
    admin_message: Optional[str] = None
    context_updated: bool = False


class WelcomeFlowManager:
    """Manages the new user welcome flow and organization data collection."""
    
    def __init__(self, 
                 database_service: DatabaseService,
                 line_service: LineService,
                 analyzer: OrganizationDataAnalyzer):
        self.db = database_service
        self.line = line_service
        self.analyzer = analyzer
    
    def handle_new_user(self, user_id: str) -> None:
        """Handle new user follow event."""
        try:
            # Create organization data record (if doesn't exist)
            org_record = self.db.get_organization_record(user_id)
            if not org_record:
                self.db.create_organization_record(user_id)
            
            # AI welcome message is now included in organization data request message
            
            # Notify admin about new user
            self.line.notify_admin(
                user_id=user_id,
                user_msg="新用戶加入 LINE Bot - 等待提供組織資料",
                notification_type="new_user"
            )
            
            logger.info(f"New user {user_id} added to welcome flow")
            
        except Exception as e:
            logger.error(f"Error handling new user {user_id}: {e}")
    
    def process_message(self, user_id: str, message: str) -> WelcomeFlowResult:
        """
        Process user message in the context of welcome flow.
        
        Args:
            user_id: User's LINE ID
            message: User's message
            
        Returns:
            WelcomeFlowResult indicating what actions to take
        """
        try:
            # Check if user has completed organization data
            org_record = self.db.get_organization_record(user_id)
            
            if not org_record:
                # User not in system, create record
                self.db.create_organization_record(user_id)
                org_record = self.db.get_organization_record(user_id)
            
            # If already complete, allow normal flow
            if org_record.get('completion_status') == 'complete':
                return WelcomeFlowResult(should_block=False)
            
            # Check if it's a handover request
            if self._is_handover_request(message):
                return WelcomeFlowResult(
                    should_block=False,  # Allow handover through
                    response_message=None  # Let normal flow handle it
                )
            
            # Analyze message for organization data
            current_data = self._record_to_data(org_record)
            analysis_result = self.analyzer.analyze_message(message, current_data)
            
            # Update database with new data
            self.db.update_organization_record(
                user_id=user_id,
                organization_data=analysis_result['extracted_data'],
                completion_status=analysis_result['completion_status'],
                raw_message=message
            )
            
            # Check if completed
            if analysis_result['completion_status'] == 'complete':
                # Get the updated organization data for admin notification
                updated_record = self.db.get_organization_record(user_id)
                org_data = self._record_to_data(updated_record)
                
                # Format organization data for admin message
                admin_message = "已完成組織資料填寫\n\n"
                admin_message += f"組織名稱: {org_data.organization_name or '未提供'}\n"
                admin_message += f"服務城市: {org_data.service_city or '未提供'}\n"
                admin_message += f"聯絡資訊: {org_data.contact_info or '未提供'}\n"
                admin_message += f"服務對象: {org_data.service_target or '未提供'}"
                
                return WelcomeFlowResult(
                    should_block=True,
                    response_message=analysis_result['hint_message'],
                    notify_admin=True,
                    admin_message=admin_message,
                    context_updated=True
                )
            else:
                # Still missing data, send hint
                return WelcomeFlowResult(
                    should_block=True,
                    response_message=analysis_result['hint_message']
                )
                
        except Exception as e:
            logger.error(f"Error processing welcome flow for user {user_id}: {e}")
            return WelcomeFlowResult(
                should_block=True,
                response_message="系統暫時無法處理您的請求，請稍後再試。"
            )
    
    def _is_handover_request(self, message: str) -> bool:
        """Check if message is a handover request."""
        return message.strip() == "轉人工"
    
    def _record_to_data(self, record: Dict) -> OrganizationData:
        """Convert database record to OrganizationData."""
        if not record:
            return OrganizationData()
        
        return OrganizationData(
            organization_name=record.get('organization_name'),
            service_city=record.get('service_city'),
            contact_info=record.get('contact_info'),
            service_target=record.get('service_target')
        )
    
    def get_user_completion_status(self, user_id: str) -> str:
        """Get user's organization data completion status."""
        try:
            record = self.db.get_organization_record(user_id)
            if not record:
                return 'pending'
            return record.get('completion_status', 'pending')
        except Exception as e:
            logger.error(f"Error getting completion status for user {user_id}: {e}")
            return 'pending'
    
    def reset_user_flow(self, user_id: str) -> None:
        """Reset user's welcome flow (for admin use)."""
        try:
            self.db.reset_organization_record(user_id)
            logger.info(f"Welcome flow reset for user {user_id}")
        except Exception as e:
            logger.error(f"Error resetting welcome flow for user {user_id}: {e}")