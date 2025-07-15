"""
Database service for managing database connections and operations.
"""
import pymysql
from typing import Optional, Dict, Any
from contextlib import contextmanager

from config import config
from src.utils import setup_logger, DatabaseError
from src.models import User


logger = setup_logger(__name__)


class DatabaseService:
    """Service for database operations."""
    
    def __init__(self):
        self.config = config.database
        
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        connection = None
        try:
            connection_params = {
                'host': self.config.host,
                'user': self.config.user,
                'database': self.config.database,
                'charset': self.config.charset
            }
            
            if self.config.password:
                connection_params['password'] = self.config.password
                
            connection = pymysql.connect(**connection_params)
            yield connection
        except pymysql.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
        finally:
            if connection:
                connection.close()
    
    def initialize_tables(self):
        """Initialize required database tables."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # User threads table
                create_user_threads_sql = """
                CREATE TABLE IF NOT EXISTS user_threads (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL UNIQUE,
                    thread_id VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_thread_id (thread_id)
                );
                """
                
                # Message history table
                create_messages_sql = """
                CREATE TABLE IF NOT EXISTS message_history (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
                    message_type VARCHAR(20) DEFAULT 'text',
                    ai_response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
                    confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                );
                """
                
                cursor.execute(create_user_threads_sql)
                cursor.execute(create_messages_sql)
                conn.commit()
                
                logger.info("Database tables initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            raise DatabaseError(f"Table initialization failed: {e}")
    
    def get_user_thread_id(self, user_id: str) -> Optional[str]:
        """Get thread ID for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT thread_id FROM user_threads WHERE user_id = %s AND is_active = TRUE",
                    (user_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get thread ID for user {user_id}: {e}")
            raise DatabaseError(f"Failed to retrieve thread ID: {e}")
    
    def set_user_thread_id(self, user_id: str, thread_id: str) -> None:
        """Set thread ID for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_threads (user_id, thread_id) 
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE 
                    thread_id = VALUES(thread_id),
                    updated_at = CURRENT_TIMESTAMP
                """, (user_id, thread_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to set thread ID for user {user_id}: {e}")
            raise DatabaseError(f"Failed to set thread ID: {e}")
    
    def reset_user_thread(self, user_id: str) -> None:
        """Reset user's thread by marking as inactive."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_threads SET is_active = FALSE WHERE user_id = %s",
                    (user_id,)
                )
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to reset thread for user {user_id}: {e}")
            raise DatabaseError(f"Failed to reset thread: {e}")
    
    def log_message(self, user_id: str, content: str, message_type: str = "text", 
                   ai_response: str = None, confidence: float = None) -> None:
        """Log message interaction to database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO message_history 
                    (user_id, content, message_type, ai_response, confidence) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, content, message_type, ai_response, confidence))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log message for user {user_id}: {e}")
            # Don't raise exception for logging failures to avoid disrupting main flow
            pass