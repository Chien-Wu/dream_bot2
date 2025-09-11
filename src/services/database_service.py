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
    
    def execute_query(self, query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False):
        """
        Execute a SQL query with parameters.
        
        Args:
            query: SQL query string
            params: Query parameters tuple
            fetch_one: Return single row
            fetch_all: Return all rows
            
        Returns:
            Query results or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, params or ())
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.rowcount
                    
        except pymysql.Error as e:
            logger.error(f"Query execution error: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def initialize_tables(self):
        """Initialize required database tables."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # User threads table
                create_user_threads_sql = """
                CREATE TABLE IF NOT EXISTS user_threads (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
                    thread_id VARCHAR(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
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
                    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    message_type VARCHAR(20) DEFAULT 'text',
                    ai_response TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    ai_explanation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    confidence DECIMAL(3,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at)
                );
                """
                
                # Organization data table
                create_organization_sql = """
                CREATE TABLE IF NOT EXISTS organization_data (
                    user_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PRIMARY KEY,
                    organization_name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    service_city VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    contact_info TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    service_target VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    completion_status ENUM('pending', 'partial', 'complete') DEFAULT 'pending',
                    raw_messages TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_completion_status (completion_status),
                    INDEX idx_created_at (created_at)
                );
                """
                
                cursor.execute(create_user_threads_sql)
                cursor.execute(create_messages_sql)
                cursor.execute(create_organization_sql)
                
                # Add explanation column if it doesn't exist (for existing installations)
                cursor.execute("SHOW COLUMNS FROM message_history LIKE 'ai_explanation'")
                column_exists = cursor.fetchone()
                
                if not column_exists:
                    logger.info("Adding ai_explanation column to message_history table...")
                    cursor.execute("ALTER TABLE message_history ADD COLUMN ai_explanation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    logger.info("ai_explanation column added successfully")
                else:
                    logger.info("ai_explanation column already exists")
                
                # Create ai_detail table if it doesn't exist (for existing installations)
                cursor.execute("SHOW TABLES LIKE 'ai_detail'")
                table_exists = cursor.fetchone()
                
                if not table_exists:
                    logger.info("Creating ai_detail table...")
                    create_ai_detail_sql = """
                        CREATE TABLE ai_detail (
                            id INT PRIMARY KEY AUTO_INCREMENT,
                            message_history_id INT,
                            intent VARCHAR(50),
                            queries JSON,
                            sources JSON,
                            gaps JSON,
                            policy_scope TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                            policy_risk TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                            policy_pii TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                            policy_escalation TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                            notes TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_message_history_id (message_history_id),
                            INDEX idx_intent (intent),
                            INDEX idx_created_at (created_at),
                            FOREIGN KEY (message_history_id) REFERENCES message_history(id) ON DELETE CASCADE
                        )
                    """
                    cursor.execute(create_ai_detail_sql)
                    logger.info("ai_detail table created successfully")
                else:
                    logger.info("ai_detail table already exists")
                
                # Add handover flag column if it doesn't exist (for existing installations)
                cursor.execute("SHOW COLUMNS FROM organization_data LIKE 'handover_flag_expires_at'")
                handover_column_exists = cursor.fetchone()
                
                if not handover_column_exists:
                    logger.info("Adding handover_flag_expires_at column to organization_data table...")
                    cursor.execute("""
                        ALTER TABLE organization_data 
                        ADD COLUMN handover_flag_expires_at TIMESTAMP NULL,
                        ADD INDEX idx_handover_expires (handover_flag_expires_at)
                    """)
                    logger.info("handover_flag_expires_at column added successfully")
                else:
                    logger.info("handover_flag_expires_at column already exists")
                
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
                   ai_response: str = None, ai_explanation: str = None, confidence: float = None) -> int:
        """Log message interaction to database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO message_history 
                    (user_id, content, message_type, ai_response, ai_explanation, confidence) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (user_id, content, message_type, ai_response, ai_explanation, confidence))
                conn.commit()
                return cursor.lastrowid  # Return message_history ID for linking
                
        except Exception as e:
            logger.error(f"Failed to log message for user {user_id}: {e}")
            # Don't raise exception for logging failures to avoid disrupting main flow
            return None
    
    def save_ai_detail(self, message_history_id: int, ai_response) -> None:
        """Save AI detail data to ai_detail table."""
        try:
            logger.info(f"[AI_DETAIL] Starting save_ai_detail for message_history_id: {message_history_id}")
            
            # Check if message_history_id is valid
            if not message_history_id:
                logger.warning(f"[AI_DETAIL] Invalid message_history_id: {message_history_id}")
                return
            
            # Check what extended data we have
            has_data = {
                'intent': bool(ai_response.intent),
                'queries': bool(ai_response.queries),
                'sources': bool(ai_response.sources),
                'gaps': bool(ai_response.gaps),
                'policy_escalation': bool(ai_response.policy_escalation),
                'policy_scope': bool(ai_response.policy_scope),
                'policy_risk': bool(ai_response.policy_risk),
                'policy_pii': bool(ai_response.policy_pii),
                'notes': bool(ai_response.notes)
            }
            
            logger.info(f"[AI_DETAIL] Extended data check: {has_data}")
            
            # Only save if we have any extended schema data
            if not any(has_data.values()):
                logger.info(f"[AI_DETAIL] No extended data to save, skipping")
                return
            
            import json
            
            logger.info(f"[AI_DETAIL] Proceeding to save data to database")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ai_detail 
                    (message_history_id, intent, queries, sources, gaps, 
                     policy_scope, policy_risk, policy_pii, policy_escalation, notes) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    message_history_id,
                    ai_response.intent,
                    json.dumps(ai_response.queries) if ai_response.queries else None,
                    json.dumps(ai_response.sources) if ai_response.sources else None,
                    json.dumps(ai_response.gaps) if ai_response.gaps else None,
                    ai_response.policy_scope,
                    ai_response.policy_risk,
                    ai_response.policy_pii,
                    ai_response.policy_escalation,
                    ai_response.notes
                ))
                conn.commit()
                logger.info(f"[AI_DETAIL] Successfully saved AI detail for message_history_id: {message_history_id}")
                
        except Exception as e:
            logger.error(f"[AI_DETAIL] Failed to save AI detail for message_history_id {message_history_id}: {e}")
            # Don't raise exception for logging failures to avoid disrupting main flow
            pass
    
    def create_organization_record(self, user_id: str) -> None:
        """Create a new organization data record for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO organization_data (user_id, completion_status) 
                    VALUES (%s, 'pending')
                    ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                """, (user_id,))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create organization record for user {user_id}: {e}")
            raise DatabaseError(f"Failed to create organization record: {e}")
    
    def get_organization_record(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get organization data record for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("""
                    SELECT * FROM organization_data WHERE user_id = %s
                """, (user_id,))
                result = cursor.fetchone()
                return result
                
        except Exception as e:
            logger.error(f"Failed to get organization record for user {user_id}: {e}")
            raise DatabaseError(f"Failed to retrieve organization record: {e}")
    
    def update_organization_record(self, user_id: str, organization_data, 
                                 completion_status: str, raw_message: str = None) -> None:
        """Update organization data record."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query based on provided data
                update_fields = []
                params = []
                
                if organization_data.organization_name:
                    update_fields.append("organization_name = %s")
                    params.append(organization_data.organization_name)
                
                if organization_data.service_city:
                    update_fields.append("service_city = %s")
                    params.append(organization_data.service_city)
                
                if organization_data.contact_info:
                    update_fields.append("contact_info = %s")
                    params.append(organization_data.contact_info)
                
                if organization_data.service_target:
                    update_fields.append("service_target = %s")
                    params.append(organization_data.service_target)
                
                update_fields.append("completion_status = %s")
                params.append(completion_status)
                
                if raw_message:
                    update_fields.append("raw_messages = CONCAT(COALESCE(raw_messages, ''), %s)")
                    params.append(f"\n{raw_message}")
                
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                
                query = f"""
                    UPDATE organization_data 
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s
                """
                
                cursor.execute(query, params + [user_id])
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update organization record for user {user_id}: {e}")
            raise DatabaseError(f"Failed to update organization record: {e}")
    
    def reset_organization_record(self, user_id: str) -> None:
        """Reset organization data record for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE organization_data 
                    SET organization_name = NULL,
                        service_city = NULL,
                        contact_info = NULL,
                        service_target = NULL,
                        completion_status = 'pending',
                        raw_messages = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to reset organization record for user {user_id}: {e}")
            raise DatabaseError(f"Failed to reset organization record: {e}")
    
