import mysql.connector
import os

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "line_bot")

def get_db():
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    return conn

def get_thread_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT thread_id FROM user_threads WHERE user_id=%s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None

def set_thread_id(user_id, thread_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_threads (user_id, thread_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE thread_id=%s",
        (user_id, thread_id, thread_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def reset_thread_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_threads WHERE user_id=%s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()