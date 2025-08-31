"""
User handover flag service for managing human handover states.
"""
from typing import Optional

from src.utils import setup_logger, DatabaseError
from src.services.database_service import DatabaseService


logger = setup_logger(__name__)


class UserHandoverService:
    """Service for managing user handover flags."""
    
    def __init__(self, database_service: DatabaseService):
        self.db = database_service
    
    def set_handover_flag(self, user_id: str, hours: int = 1) -> None:
        """
        Set handover flag for user with expiry time.
        
        Args:
            user_id: User's LINE ID
            hours: Hours until flag expires (default: 1)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ensure user has organization record
                cursor.execute("""
                    INSERT INTO organization_data (user_id, completion_status) 
                    VALUES (%s, 'pending')
                    ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                """, (user_id,))
                
                # Set handover flag
                cursor.execute("""
                    UPDATE organization_data 
                    SET handover_flag_expires_at = DATE_ADD(NOW(), INTERVAL %s HOUR),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (hours, user_id))
                
                conn.commit()
                logger.info(f"Handover flag set for user {user_id} for {hours} hour(s)")
                
        except Exception as e:
            logger.error(f"Failed to set handover flag for user {user_id}: {e}")
            raise DatabaseError(f"Failed to set handover flag: {e}")
    
    def is_in_handover(self, user_id: str) -> bool:
        """
        Check if user is currently in handover mode.
        
        Args:
            user_id: User's LINE ID
            
        Returns:
            True if user has active handover flag
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT handover_flag_expires_at 
                    FROM organization_data 
                    WHERE user_id = %s 
                    AND handover_flag_expires_at > NOW()
                """, (user_id,))
                
                result = cursor.fetchone()
                is_flagged = result is not None
                
                if is_flagged:
                    logger.debug(f"User {user_id} is in handover mode")
                
                return is_flagged
                
        except Exception as e:
            logger.error(f"Failed to check handover flag for user {user_id}: {e}")
            # Fail-safe: allow AI processing if DB error
            return False
    
    def clear_handover_flag(self, user_id: str) -> None:
        """
        Manually clear handover flag for user.
        
        Args:
            user_id: User's LINE ID
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE organization_data 
                    SET handover_flag_expires_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Handover flag cleared for user {user_id}")
                else:
                    logger.debug(f"No handover flag to clear for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to clear handover flag for user {user_id}: {e}")
            raise DatabaseError(f"Failed to clear handover flag: {e}")
    
    def cleanup_expired_flags(self) -> int:
        """
        Clean up expired handover flags.
        
        Returns:
            Number of flags cleaned up
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE organization_data 
                    SET handover_flag_expires_at = NULL 
                    WHERE handover_flag_expires_at <= NOW()
                """)
                
                conn.commit()
                count = cursor.rowcount
                
                if count > 0:
                    logger.info(f"Cleaned up {count} expired handover flags")
                
                return count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired handover flags: {e}")
            return 0
    
    def get_handover_status(self, user_id: str) -> Optional[dict]:
        """
        Get detailed handover status for user (for admin commands).
        
        Args:
            user_id: User's LINE ID
            
        Returns:
            Dict with handover details or None if not in handover
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT handover_flag_expires_at,
                           TIMESTAMPDIFF(MINUTE, NOW(), handover_flag_expires_at) as minutes_left
                    FROM organization_data 
                    WHERE user_id = %s 
                    AND handover_flag_expires_at > NOW()
                """, (user_id,))
                
                result = cursor.fetchone()
                
                if result:
                    return {
                        'expires_at': result[0],
                        'minutes_left': result[1],
                        'is_active': True
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get handover status for user {user_id}: {e}")
            return None