import os
import logging
from typing import Optional

from mysql.connector import pooling, Error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "line_bot")
POOL_NAME = os.getenv("MYSQL_POOL_NAME", "line_bot_pool")
POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", "5"))

try:
    pool = pooling.MySQLConnectionPool(
        pool_name=POOL_NAME,
        pool_size=POOL_SIZE,
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        autocommit=False
    )
    logger.info(f"已建立資料庫連線池 '{POOL_NAME}' (size={POOL_SIZE})")
except Error as e:
    logger.exception("無法初始化資料庫連線池")
    raise


def _get_connection():
    """
    從連線池取得一個連線。
    """
    try:
        return pool.get_connection()
    except Error:
        logger.exception("無法從連線池取得連線")
        raise


def get_thread_id(user_id: str) -> Optional[str]:
    """
    取得指定使用者的 thread_id，若不存在則回傳 None。
    """
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT thread_id FROM user_threads WHERE user_id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Error:
        logger.exception(f"查詢 user_id={user_id} 時發生錯誤")
        return None


def set_thread_id(user_id: str, thread_id: str) -> bool:
    """
    插入或更新使用者的 thread_id，成功回傳 True，否則 False。
    """
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO user_threads (user_id, thread_id) VALUES (%s,%s) "
                "ON DUPLICATE KEY UPDATE thread_id = VALUES(thread_id)",
                (user_id, thread_id)
            )
        conn.commit()
        conn.close()
        return True
    except Error:
        logger.exception(f"儲存 thread_id for user_id={user_id} 時發生錯誤")
        return False


def reset_thread_id(user_id: str) -> bool:
    """
    刪除指定使用者的 thread_id，成功回傳 True，否則 False。
    """
    try:
        conn = _get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_threads WHERE user_id = %s",
                (user_id,)
            )
        conn.commit()
        conn.close()
        return True
    except Error:
        logger.exception(f"刪除 thread_id for user_id={user_id} 時發生錯誤")
        return False
